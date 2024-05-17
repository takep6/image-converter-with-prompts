import os
import signal
import stat
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import piexif
import piexif.helper
import pillow_avif
from PIL import Image, PngImagePlugin

import image_converter.const as exts


def is_supported_extension(path):
    """
    ファイルのヘッダーから拡張子を判定する
    """
    with open(path, 'rb') as f:
        header = f.read(16)  # ファイルの先頭16バイトを読み込む
        return header.startswith(exts.SUPPORTED_EXTENSIONS_BIN)


def get_output_fullpath(output_folder_path, filename, ext):
    return f"{output_folder_path}/{filename}.{ext}"


def extract_metadata(image, input_path):
    """
    画像のExif（メタデータ）を取得する
    """
    metadata = {}
    if input_path.lower().endswith(exts.PNG_EXT):
        metadata = image.info
    elif input_path.lower().endswith((exts.JPEG_EXT, exts.JPG_EXT, exts.WEBP_EXT, exts.AVIF_EXT)):
        if "exif" in image.info.keys():
            exif_dict = piexif.load(image.info["exif"])
            if piexif.ExifIFD.UserComment in exif_dict["Exif"]:
                user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
                metadata = {
                    "parameters": piexif.helper.UserComment.load(user_comment)}
    return metadata


def fill_image_with_fill_color(image, fill_color):
    """
    透過部分を指定した色で塗りつぶす
    """
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        background = Image.new("RGB", image.size, fill_color)
        background.paste(image, mask=image.split()[3])  # アルファチャンネルをマスクとして使用
        image = background
    return image


def save_with_metadata(image, output_fullpath, output_format, quality, metadata, lossless):
    """
    画像を指定の拡張子で保存する
    is_fill_transparentがTrueなら"RGB", Falseなら"RGBA"に変換される
    """
    ext = output_format.lower()
    exif_bytes = None

    # Exif情報（メタデータ）を拡張子に合わせて整形
    if ext == exts.PNG_EXT:
        metadata_obj = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata_obj.add_text(key, value)
        # pngのみpnginfoに保存する必要がある
        image.save(output_fullpath, format=ext, pnginfo=metadata_obj,
                   quality=quality, lossless=lossless)
        return
    elif ext in (exts.JPEG_EXT, exts.JPG_EXT, exts.WEBP_EXT, exts.AVIF_EXT):
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})

    else:
        raise ValueError(f"Invalid output format: {output_format}")

    # extがjpgのとき、format="jpg"ではエラーが起こるため"jpeg"に変換
    ext = exts.JPEG_EXT if ext == exts.JPG_EXT else ext
    # メタデータ付き画像を保存
    image.save(output_fullpath, format=ext, quality=quality,
               exif=exif_bytes, lossless=lossless)


def get_path_pairs(input_path, output_folder_path, output_format):
    """
    入力ファイルのパスと出力フォルダのパスのペアを返す
    """
    # 出力する画像ファイルとあらかじめ出力フォルダに
    # 存在するファイル名が重複しないようにする
    existed_output_filenames = set()
    for filename in os.listdir(output_folder_path):
        basename, ext = os.path.splitext(filename)
        ext = ext.replace(".", "").lower()  # 拡張子の"."を削除
        if ext == output_format:
            existed_output_filenames.add(basename)

    paths = {}
    # input_pathがファイル単体の場合
    if os.path.isfile(input_path):
        filename = os.path.basename(input_path)
        basename = os.path.splitext(filename)[0]
        counter = 1
        unique_name = basename
        # ユニークなファイル名を作成
        while unique_name in existed_output_filenames:
            unique_name = f"{basename}_{counter:03d}"
            counter += 1
        output_fullpath = get_output_fullpath(
            output_folder_path, unique_name, output_format)
        paths[input_path] = output_fullpath  # パスのペア作成
        return paths

    # 複数ファイルの場合

    # フォルダ内のファイルのみを取得する
    filenames = [f for f in os.listdir(input_path) if os.path.isfile(
        os.path.join(input_path, f))]
    for filename in filenames:
        input_fullpath = os.path.join(input_path, filename)
        # 関係のないファイルは除外
        if not is_supported_extension(input_fullpath):
            continue
        # ユニークなファイル名を作成
        counter = 1
        basename = os.path.splitext(filename)[0]
        unique_name = basename
        # dictへのinによるキーの存在確認はO(1) で実行される
        while unique_name in existed_output_filenames:
            unique_name = f"{basename}_{counter:03d}"
            counter += 1
        existed_output_filenames.add(unique_name)

        # ファイルパスのペアを作成

        output_fullpath = get_output_fullpath(
            output_folder_path, unique_name, output_format)
        paths[input_fullpath] = output_fullpath
    return paths


def convert_image(conversion_params):
    """
    画像の変換を行う
    """
    input_path, output_path, output_format, quality, lossless, is_fill_color, fill_color = conversion_params

    with Image.open(input_path) as image:
        # アニメーション画像は変換しない
        if input_path.endswith((exts.PNG_EXT, exts.WEBP_EXT, exts.AVIF_EXT)):
            if image.is_animated:
                return
        # 透明部分を塗りつぶす
        if is_fill_color:
            image = fill_image_with_fill_color(image, fill_color)
        # 画像のプロンプト情報を取得
        metadata = extract_metadata(image, input_path)
        # 保存
        save_with_metadata(image, output_path, output_format,
                           quality, metadata, lossless)


def can_convert(path):
    # 画像ファイル単体の場合
    if os.path.isfile(path):
        return is_supported_extension(path)

    # フォルダ内に画像ファイルが存在するかどうか
    filenames = [f for f in os.listdir(path) if os.path.isfile(
        os.path.join(path, f))]
    for file in filenames:
        fullpath = os.path.join(path, file)
        if is_supported_extension(fullpath):
            return True
    return False


def convert_images_concurrently(conversion_params):
    """
    プロセスの実行をして、画像の変換を並行処理で行う
    """
    input_path, output_folder_path, output_format, quality, lossless, is_fill_color, fill_color, cpu_num = conversion_params

    os.makedirs(output_folder_path, exist_ok=True)
    global should_stop
    isError = False
    message = ""

    if not can_convert(input_path):
        # isError = True
        message = "変換可能な画像ファイルがありません"
        return isError, message

    try:
        # input_pathとoutput_folder_pathのペアを作成
        path_pairs = get_path_pairs(
            input_path, output_folder_path, output_format)
        # プロセス準備
        with ProcessPoolExecutor(max_workers=cpu_num) as executor:
            futures = []
            for input_fullpath, output_fullpath in path_pairs.items():
                if should_stop:
                    break
                futures.append(executor.submit(
                    convert_image,
                    (input_fullpath,
                        output_fullpath,
                        output_format,
                        quality,
                        lossless,
                        is_fill_color,
                        fill_color)))

            # プロセス実行
            for future in as_completed(futures):
                if should_stop:
                    raise Exception("画像の変換処理をキャンセルしました")
                _ = future.result()
            print(message)

    except PermissionError as e:
        isError = True
        message = "画像ファイルを変換する権限がありません"
        print("画像ファイルを変換する権限がありません" + str(e))
        return isError, message

    except Exception as e:
        isError = True
        if should_stop:
            message = "画像の変換処理をキャンセルしました"
        else:
            message = "変換中にエラーが発生しました"
        print(message + str(e))
        # Futureをキャンセル
        for future in futures:
            if not future.running():
                future.cancel()
        return isError, message

    except KeyboardInterrupt:
        # ctrl+cで終了した場合
        # プロセスに終了要求(データが不完全でも終了)
        isError = True
        message = "プロセスの強制終了が要求されました"
        print(message)
        for process in executor._processes.values():
            process.terminate()
        return isError, message

    message = "画像の変換処理が完了しました"

    return isError, message


def convert_images_all_subfolders(conversion_params):
    """
    全フォルダの画像を変換する
    """
    isError = False
    message = ""

    input_path, output_folder_path, output_format, quality, lossless, is_fill_color, fill_color, cpu_num = conversion_params

    # 画像単体の場合
    if not os.path.isdir(input_path):
        isError, message = convert_images_concurrently(conversion_params)
        return isError, message

    # サブフォルダを含めた全ての入力フォルダパスを取得
    all_input_folder_paths = [input_path]
    for root, folder_names, _ in os.walk(input_path):
        all_input_folder_paths.extend(
            [os.path.join(root, folder) for folder in folder_names])

    print(all_input_folder_paths)

    # フォルダ数が多すぎる場合は処理を中断する
    if len(all_input_folder_paths) >= 10000:
        isError = True
        message = "フォルダ数が多すぎます。処理を中断します。"
        return isError, message

    # 全てのフォルダで変換を実行
    for input_folder_path in all_input_folder_paths:
        if isError:
            break
        output_path = input_folder_path.replace(
            input_path, output_folder_path)
        params = (input_folder_path, output_path, output_format,
                  quality, lossless, is_fill_color, fill_color, cpu_num)
        isError, message = convert_images_concurrently(params)

    return isError, message


# プロセス停止用
should_stop = False
stop_lock = threading.Lock()


def stop_process():
    global should_stop
    with stop_lock:
        should_stop = True


def set_signals():
    # ctrl+cなど異常終了時にシグナルを受け取る
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def signal_handler(sig, frame):
    stop_process()
    sys.exit(0)
