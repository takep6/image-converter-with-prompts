import os
import signal
import sys
import threading
import time
from concurrent.futures import (ProcessPoolExecutor, ThreadPoolExecutor,
                                as_completed)

import piexif
import piexif.helper
import pillow_avif
from PIL import Image, PngImagePlugin

SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".avif")
PNG_EXT = "png"
JPG_EXT = "jpg"
JPEG_EXT = "jpeg"
WEBP_EXT = "webp"
AVIF_EXT = "avif"
PNG_EXT_BIN = b'\x89PNG\r\n\x1a\n'
JPG_EXT_BIN = b'\xff\xd8\xff'
JPEG_EXT_BIN = b'\xff\xd8\xdd'
WEBP_EXT_BIN = b'RIFF'
AVIF_EXT_BIN = b'\x00\x00\x00\x20ftypavif'


def is_supported_extension(file_path):
    """
    ファイルのマジックナンバーから拡張子を判定する
    """
    with open(file_path, 'rb') as f:
        header = f.read(16)  # ファイルの先頭16バイトを読み込む
        return header.startswith(PNG_EXT_BIN) or \
            header.startswith(JPG_EXT_BIN) or \
            header.startswith(JPEG_EXT_BIN) or \
            header.startswith(WEBP_EXT_BIN) or \
            header.startswith(AVIF_EXT_BIN)


def get_output_fullpath(output_folder_path, filename, ext):
    return f"{output_folder_path}/{filename}.{ext}"


def extract_metadata(image, input_path):
    metadata = {}
    if input_path.lower().endswith(PNG_EXT):
        metadata = image.info
    elif input_path.lower().endswith((JPEG_EXT, JPG_EXT, WEBP_EXT, AVIF_EXT)):
        if "exif" in image.info.keys():
            exif_dict = piexif.load(image.info["exif"])
            if piexif.ExifIFD.UserComment in exif_dict["Exif"]:
                user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
                metadata = {
                    "parameters": piexif.helper.UserComment.load(user_comment)}
    return metadata


def convert_with_transparent_color(image, transparent_color):
    # 透過部分を指定した色でフィルする
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        background = Image.new("RGB", image.size, transparent_color)
        background.paste(image, mask=image.split()[3])  # アルファチャンネルをマスクとして使用
        image = background
    return image


def save_with_metadata(image, output_fullpath, output_format, quality, metadata, lossless, is_fill_transparenct, transparent_color):
    """
    画像を指定の拡張子で保存する
    is_fill_transparentがTrueなら"RGB", Falseなら"RGBA"に変換される
    """
    ext = output_format.lower()
    exif_bytes = None

    if ext == PNG_EXT:
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        metadata_obj = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata_obj.add_text(key, value)
    elif ext in (JPEG_EXT, JPG_EXT):
        if image.mode == "RGBA":
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
    elif ext == WEBP_EXT:
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
    elif ext == AVIF_EXT:
        image.encoderinfo = {}
        image.encoderinfo['alpha_premultiplied'] = False
        image.encoderinfo['autotiling'] = True
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
    else:
        raise ValueError(f"Invalid output format: {output_format}")

    # jpgの場合のみJPEGに変換、それ以外はスルー
    ext = JPEG_EXT if ext == JPG_EXT else ext
    # メタデータ付き画像を保存
    image.save(output_fullpath, format=ext, quality=quality,
               exif=exif_bytes, lossless=lossless)


def convert_image(settings):
    input_path, output_path, output_format, quality, lossless, is_fill_transparenct, transparent_color = settings

    with Image.open(input_path) as image:
        # if output_format == PNG_EXT or output_format == WEBP_EXT or output_format == AVIF_EXT:
        #     if image.is_animated:
        #         return
        metadata = extract_metadata(image, input_path)
        save_with_metadata(image, output_path, output_format,
                           quality, metadata, lossless, is_fill_transparenct, transparent_color)


def convert_images_in_folder(settings):
    global should_stop
    should_stop = False

    input_path, output_folder_path, output_format, quality, lossless, is_fill_transparenct, transparent_color, cpu_num = settings

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
                           is_fill_transparenct,
                           transparent_color))
        except Exception as e:
            raise ValueError(f"変換中にエラーが発生しました: {e}")

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
                             is_fill_transparenct,
                             transparent_color)))
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
                print(f"Task generated an exception: {e}")
                # Futureをキャンセル
                for future in futures:
                    if not future.running():
                        future.cancel()
                raise Exception("画像の変換を停止しました")
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
        raise ValueError(f"未対応のファイル形式です。")


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
