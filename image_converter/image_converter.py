import ast
import json
import os
import signal
import sys
import threading
import traceback
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


def convert_webui_to_novelai(metadata):
    """
    jpg, webp, avif向けに変換したNovelAIの画像のメタデータを(png向けに)復元する
    """
    try:
        # "NAI:"以降の文字列を抽出してdict型に変換してから返す
        md = metadata["parameters"][metadata["parameters"].find(
            "NAI:")+4:].strip()
        return ast.literal_eval(md)
    except Exception:
        tb = traceback.format_exc()
        print(f"NovelAIのメタデータの取得に失敗しました\n{tb}")


def convert_webui_to_comfyui(metadata):
    """
    jpg, webp, avif向けに変換したComfyUIの画像のメタデータを(png向けに)復元する
    """
    try:
        # "ComfyUI:"以降の文字列を抽出してdict型に変換してから返す
        md = metadata["parameters"][metadata["parameters"].find(
            "ComfyUI:")+8:].strip()
        return ast.literal_eval(md)
    except Exception:
        tb = traceback.format_exc()
        print(f"ComfyUIのメタデータの取得に失敗しました\n{tb}")


def convert_novelai_to_webui(metadata):
    """
    NovelAIの画像のメタデータをa1111(WebUI)で読み込める形式に変換する
    jpg, webp, avif形式に変換してもNovelAIの画像のメタデータが残るように変換している
    """
    try:
        json_info = json.loads(metadata["Comment"])

        geninfo = f"""{metadata["Description"]}
Negative prompt: {json_info["uc"]}
Steps: {json_info["steps"]}, Sampler: {json_info["sampler"]}, CFG scale: {json_info["scale"]}, Seed: {json_info["seed"]}, Size: {json_info["width"]}x{json_info["height"]}, Clip skip: 2, ENSD: 31337, NAI: {metadata}"""
    except Exception:
        print("Error parsing NovelAI image generation parameters")

    return geninfo


def convert_comfyui_to_webui(metadata):
    """
    jpg, webp, avif形式に変換してもComfyUIの画像のメタデータが残るように変換している
    """
    return f"ComfyUI: {metadata}"


def save_with_metadata(image, output_fullpath, output_format, quality, metadata, lossless):
    """
    画像を指定の拡張子で保存する
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
        if metadata.get("Software", None) == "NovelAI":
            # NovelAIはWebUIで読み込める形にメタデータを変換する
            md = convert_novelai_to_webui(metadata)
        elif "prompt" in metadata or "workflow" in metadata:
            # ComfyUIはそのままメタデータを保存
            md = convert_comfyui_to_webui(metadata)
        else:
            # WebUIまたはその他のメタデータを保存
            md = metadata.get("parameters", "")
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            md, encoding="unicode")}})

    else:
        raise ValueError(f"Invalid output format: {output_format}")

    # extがjpgのとき、format="jpg"ではエラーが起こるため"jpeg"に変換
    ext = exts.JPEG_EXT if ext == exts.JPG_EXT else ext
    # メタデータ付き画像を保存
    image.save(output_fullpath, format=ext, quality=quality,
               exif=exif_bytes, lossless=lossless)


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

        # 画像のプロンプト情報を取得
        metadata = extract_metadata(image, input_path)

        # NovelAIまたはComfyUIの画像を変換したことがあった場合、メタデータを復元する
        if metadata.get("parameters", None):
            if "NAI:" in metadata["parameters"]:
                metadata = convert_webui_to_novelai(metadata)
            elif "ComfyUI:" in metadata["parameters"]:
                metadata = convert_webui_to_comfyui(metadata)

        # 透明部分を塗りつぶす
        if is_fill_color:
            image = fill_image_with_fill_color(image, fill_color)

        # 保存
        save_with_metadata(image, output_path, output_format,
                           quality, metadata, lossless)


def get_unique_filepath(input_filepath, output_folder_path, output_format):
    """
    ユニークな出力ファイルパスを取得する
    """
    filename = os.path.basename(input_filepath)
    basename, _ = os.path.splitext(filename)
    counter = 1
    unique_filename = basename

    while os.path.exists(os.path.join(
            output_folder_path,
            f"{unique_filename}.{output_format}")):
        unique_filename = f"{basename}_{counter:03d}"
        counter += 1

    return os.path.join(
        output_folder_path,
        f"{unique_filename}.{output_format}")


def get_unique_filepaths(input_filepaths, output_folder_path, output_format):
    """
    ユニークな出力ファイルパスを全て取得する
    """
    unique_fullpaths = []
    unique_filenames = set()

    for input_filepath in input_filepaths:
        filename = os.path.basename(input_filepath)
        basename, _ = os.path.splitext(filename)
        counter = 1
        unique_filename = basename
        unique_fullpath = os.path.join(
            output_folder_path,
            f"{unique_filename}.{output_format}")

        while unique_filename in unique_filenames or \
                os.path.exists(unique_fullpath):
            unique_filename = f"{basename}_{counter:03d}"
            unique_fullpath = os.path.join(
                output_folder_path,
                f"{unique_filename}.{output_format}")
            counter += 1

        unique_filenames.add(unique_filename)
        unique_fullpaths.append(unique_fullpath)

    return unique_fullpaths


def get_all_path_pairs(input_path, output_folder_path, output_format, is_convert_subfolders):
    """
    入力ファイルパスと出力ファイルパスのペアを全て取得する
    """

    path_pairs = {}
    # input_pathがファイル単体の場合
    if os.path.isfile(input_path):
        path_pairs[input_path] = get_unique_filepath(
            input_path, output_folder_path, output_format)
        os.makedirs(output_folder_path, exist_ok=True)
        return path_pairs

    # input_pathがフォルダの場合
    if is_convert_subfolders:
        # サブフォルダも全て変換
        for root, _, files in os.walk(input_path):
            input_fullpaths = [os.path.join(root, file) for file in files]
            # 変換可能なファイルのみ抽出
            convertible_paths = list(
                filter(is_supported_extension, input_fullpaths))
            if convertible_paths:
                o_folder_path = root.replace(input_path, output_folder_path)
                # フォルダが存在しなければ作成
                os.makedirs(o_folder_path, exist_ok=True)
                # 出力パスを取得
                unique_output_paths = get_unique_filepaths(
                    convertible_paths, o_folder_path, output_format)
                # 入力ファイルパスと出力ファイルパスのペアを作成
                for input_filepath, output_filepath in zip(convertible_paths, unique_output_paths):
                    path_pairs[input_filepath] = output_filepath
    else:
        # ルートフォルダのみ変換
        # input_path内の全てのファイルを取得
        input_fullpaths = [os.path.join(input_path, file)
                           for file in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, file))]
        # 変換可能なファイルのみ抽出
        convertible_paths = list(
            filter(is_supported_extension, input_fullpaths))
        if convertible_paths:
            # フォルダが存在しなければ作成
            os.makedirs(output_folder_path, exist_ok=True)
            # 出力パスを取得
            unique_output_paths = get_unique_filepaths(
                convertible_paths, output_folder_path, output_format)
            # 入力ファイルパスと出力ファイルパスのペアを作成
            for input_filepath, output_filepath in zip(convertible_paths, unique_output_paths):
                path_pairs[input_filepath] = output_filepath

    return path_pairs


def convert_images_concurrently(
        input_path,
        output_path,
        is_convert_subfolders,
        output_format,
        quality,
        is_lossless,
        is_fill_color,
        fill_color,
        cpu_num):
    """
    プロセスの実行をして、画像の変換を並行処理で行う
    """

    global should_stop
    should_stop = False
    isError = False
    message = ""

    try:
        all_file_path_pairs = get_all_path_pairs(
            input_path, output_path, output_format, is_convert_subfolders)

        if not all_file_path_pairs:
            message = "変換する画像ファイルはありません"
            return isError, message

        with ProcessPoolExecutor(max_workers=cpu_num) as executor:
            futures = []
            for input_fullpath, output_fullpath in all_file_path_pairs.items():
                if should_stop:
                    break
                futures.append(executor.submit(
                    convert_image,
                    (input_fullpath,
                        output_fullpath,
                        output_format,
                        quality,
                        is_lossless,
                        is_fill_color,
                        fill_color)))

            # プロセス実行
            for future in as_completed(futures):
                try:
                    if should_stop:
                        # Futureをキャンセル
                        for future in futures:
                            if not future.running():
                                future.cancel()
                        raise Exception()
                    else:
                        _ = future.result()
                except KeyboardInterrupt:
                    # ctrl+cで終了時
                    # 全てのプロセスに対してにエラーハンドリングする必要がある？
                    for process in executor._processes.values():
                        process.terminate()

            message = "画像の変換処理が完了しました"

    except PermissionError as e:
        isError = True
        message = "ファイルのアクセス権限がありません"
        print(f"{message}\n{e}")
        return isError, message

    except Exception as e:
        isError = True
        if should_stop:
            message = "変換処理を停止しました"
        else:
            message = "変換中にエラーが発生しました"
        error_traceback = traceback.format_exc()
        print(f"{message}\n{e}\n{error_traceback}")
        return isError, message

    return isError, message


# プロセス停止用
should_stop = False
stop_lock = threading.Lock()


# 停止ボタン・ウィンドウを閉じる際にプロセスを停止させる
def stop_process():
    global should_stop
    with stop_lock:
        should_stop = True


def set_signals():
    # ctrl+cなど異常終了時にシグナルを受け取り、プロセスを停止する
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def signal_handler(sig, frame):
    global should_stop
    with stop_lock:
        should_stop = True
    sys.exit(0)
