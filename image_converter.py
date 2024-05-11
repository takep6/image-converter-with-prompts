import os
import signal
import sys
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed

import piexif
import piexif.helper
import pillow_avif
from PIL import Image, PngImagePlugin


# outputフォルダ内のファイル重複チェック
def avoid_filename_collision(input_path, output_folder_path, output_format):
    filename, _ = os.path.splitext(os.path.basename(input_path))
    output_file_path = f"{output_folder_path}/{filename}.{output_format}"
    counter = 1
    while os.path.exists(output_file_path):
        output_file_path = f"{output_folder_path}/{filename}_{counter:02d}.{output_format}"
        counter += 1
    return output_file_path

# inputフォルダ内の同じファイル（拡張子名が違う）の重複対策


def get_unique_filepath(output_folder_path):
    return os.path.join(output_folder_path, str(uuid.uuid4()))


# 拡張子
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".avif")
PNG_EXT = "png"
JPG_EXT = "jpg"
JPEG_EXT = "jpeg"
WEBP_EXT = "webp"
AVIF_EXT = "avif"


def is_supported_extension(file_path: str) -> bool:
    # ファイルパスの拡張子が一致するかどうか
    return file_path.lower().endswith(SUPPORTED_EXTENSIONS)


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


def save_with_metadata(image, output_path, output_format, quality, metadata, lossless, is_fill_transparenct, transparent_color):
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
    image.save(output_path, format=ext, quality=quality,
               exif=exif_bytes, lossless=lossless)


def convert_image(settings):
    input_path, output_path, output_format, quality, lossless, is_fill_transparenct, transparent_color = settings

    with Image.open(input_path) as image:
        metadata = extract_metadata(image, input_path)
        save_with_metadata(image, output_path, output_format,
                           quality, metadata, lossless, is_fill_transparenct, transparent_color)


def convert_images_in_folder(settings):
    global should_stop
    should_stop = False

    input_path, output_folder_path, output_format, quality, lossless, is_fill_transparenct, transparent_color, cpu_num = settings

    # 画像ファイル単体を変換
    if os.path.isfile(input_path) and is_supported_extension(input_path):
        output_path = avoid_filename_collision(
            input_path, output_folder_path, output_format)
        try:
            convert_image((input_path, output_path, output_format,
                          quality, lossless, is_fill_transparenct, transparent_color))
        except Exception as e:
            raise ValueError(f"変換中にエラーが発生しました: {e}")
    # フォルダ内の画像を全て変換
    else:
        input_filepaths = [os.path.join(input_path, filename) for filename
                           in os.listdir(
            input_path) if is_supported_extension(filename)]

        output_filepaths = []
        output_paths_for_rename = []
        for input_filepath in input_filepaths:
            unique_path = get_unique_filepath(output_folder_path)
            output_filepaths.append(unique_path)
            # 後でリネームする用
            output_paths_for_rename.append((unique_path, input_filepath))

        with ProcessPoolExecutor(max_workers=cpu_num) as executor:
            futures = []
            for input_filepath, output_filepath in zip(input_filepaths, output_filepaths):
                if not should_stop:
                    futures.append(
                        executor.submit(
                            convert_image,
                            (input_filepath, output_filepath, output_format,
                             quality, lossless, is_fill_transparenct,
                             transparent_color)))
                else:
                    break

            try:
                start_time = time.time()

                for future in as_completed(futures):
                    if not should_stop:
                        future.result()
                    else:
                        raise Exception("画像の変換を停止しました")

                # 変換完了後にリネーム
                for unique_filepath, output_filepath in output_paths_for_rename:
                    if not should_stop:
                        o_path = avoid_filename_collision(
                            output_filepath, output_folder_path, output_format)
                        os.rename(unique_filepath, o_path)
                    else:
                        raise Exception("画像の変換を停止しました")

            except Exception as e:
                print(f"Task generated an exception: {e}")

                # Futureをキャンセル
                for future in futures:
                    if not future.running():
                        future.cancel()

                # futureの状態を確認
                # for future in futures:
                #     print(
                #         f"running: {future.running()}, cancelled: {future.cancelled()}")

                # エラーを伝播
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


def can_convert(path):
    # 画像ファイル単体の場合
    if os.path.isfile(path) and is_supported_extension(path):
        return True

    # フォルダ内に画像ファイルが存在するかどうか
    if os.path.isdir(path):
        for file in os.listdir(path):
            if is_supported_extension(file):
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
