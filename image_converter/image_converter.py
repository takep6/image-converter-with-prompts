import os
import signal
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import piexif
import piexif.helper
import pillow_avif
from PIL import Image, PngImagePlugin

import image_converter.const as exts


def is_supported_extension(file_path):
    """
    ファイルのヘッダーから拡張子を判定する
    """
    with open(file_path, 'rb') as f:
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
    elif ext in (exts.JPEG_EXT, exts.JPG_EXT, exts.WEBP_EXT):
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
    elif ext == exts.AVIF_EXT:
        image.encoderinfo = {}
        image.encoderinfo['alpha_premultiplied'] = False
        image.encoderinfo['autotiling'] = True
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
    else:
        raise ValueError(f"Invalid output format: {output_format}")

    # format="jpg"ではエラーが起こるため"jpeg"に変換
    ext = exts.JPEG_EXT if ext == exts.JPG_EXT else ext
    # メタデータ付き画像を保存
    image.save(output_fullpath, format=ext, quality=quality,
               exif=exif_bytes, lossless=lossless)


def convert_image(config):
    input_path, output_path, output_format, quality, lossless, is_fill_color, fill_color = config

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


def convert_images_in_folder(config):
    input_path, output_folder_path, output_format, quality, lossless, is_fill_color, fill_color, cpu_num = config

    os.makedirs(output_folder_path, exist_ok=True)
    global should_stop
    should_stop = False

    # 出力する画像ファイルとあらかじめ出力フォルダに
    # 存在するファイル名が重複しないようにする
    existed_output_filenames = set()
    for filename in os.listdir(output_folder_path):
        basename, ext = os.path.splitext(filename)
        ext = ext.replace(".", "").lower()  # 拡張子の"."を削除
        if ext == output_format:
            existed_output_filenames.add(basename)

    # 画像ファイル単体を変換
    if os.path.isfile(input_path) and is_supported_extension(input_path):
        counter = 1
        filename = os.path.basename(input_path)
        basename = os.path.splitext(filename)[0]
        while basename in existed_output_filenames:
            basename = f"{basename}_{counter:03d}"
            counter += 1
        output_fullpath = get_output_fullpath(
            output_folder_path, basename, output_format)

        try:
            convert_image((input_path,
                           output_fullpath,
                           output_format,
                           quality,
                           lossless,
                           is_fill_color,
                           fill_color))
        except Exception as e:
            print(f"変換中にエラーが発生しました: {e}")

    # フォルダ内の画像を全て変換
    elif os.path.isdir(input_path):
        output_filenames = set()
        paths = {}
        for filename in os.listdir(input_path):
            input_fullpath = os.path.join(input_path, filename)

            if not is_supported_extension(input_fullpath):
                continue

            # inputフォルダ内の同じファイル名（拡張子名が違う）の重複対策
            counter = 1
            basename = os.path.splitext(filename)[0]
            # dictへのinによるキーの存在確認はO(1) で実行される
            while basename in output_filenames or \
                    basename in existed_output_filenames:
                basename = f"{basename}_{counter:03d}"
                counter += 1
            output_filenames.add(basename)

            output_fullpath = get_output_fullpath(
                output_folder_path, basename, output_format)
            paths[input_fullpath] = output_fullpath

        # プロセス準備
        with ProcessPoolExecutor(max_workers=cpu_num) as executor:
            try:
                futures = []
                for input_fullpath, output_fullpath in paths.items():
                    if not should_stop:
                        futures.append(executor.submit(
                            convert_image,
                            (input_fullpath,
                             output_fullpath,
                             output_format,
                             quality,
                             lossless,
                             is_fill_color,
                             fill_color)))
                    else:
                        break

                start_time = time.time()

                # プロセス実行
                for future in as_completed(futures):
                    if not should_stop:
                        _ = future.result()
                    else:
                        raise Exception("変換処理をキャンセルしました")
            except Exception as e:
                print(f"変換中にエラーが発生しました: {e}")
                # Futureをキャンセル
                for future in futures:
                    if not future.running():
                        future.cancel()

            except KeyboardInterrupt:
                # ctrl+cで終了した場合
                # プロセスに終了要求(データが不完全でも終了)
                for process in executor._processes.values():
                    process.terminate()
            finally:
                end_time = time.time()

                if not should_stop:
                    print(
                        f"Processing completed in {end_time - start_time} seconds.")
                else:
                    raise Exception("画像の変換を停止しました")

    else:
        raise ValueError("未対応のファイル形式です。")


def can_convert(path):
    # 画像ファイル単体の場合
    if os.path.isfile(path) and is_supported_extension(path):
        return True

    # フォルダ内に画像ファイルが存在するかどうか
    if os.path.isdir(path):
        for file in os.listdir(path):
            fullpath = os.path.join(path, file)
            if is_supported_extension(fullpath):
                return True
    return False


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
