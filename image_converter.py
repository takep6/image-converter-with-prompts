import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import piexif
import piexif.helper
import pillow_avif
import psutil
from PIL import Image, PngImagePlugin


def get_unique_filename(input_path, output_folder_path, output_format, counter=1):
    # inputフォルダ内の同じファイル（拡張子名が違う）の重複対策
    basename = os.path.basename(input_path)
    filename, _ = os.path.splitext(basename)
    output_path = f"{output_folder_path}/{filename}-{counter:05d}.{output_format}"
    # outputフォルダ内のファイル重複チェック
    dup_count = 1
    while os.path.exists(output_path):
        output_path = f"{output_folder_path}/{filename}-{counter:05d}_{dup_count:02d}.{output_format}"
        dup_count += 1
    return output_path


# 拡張子
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".avif")
PNG_EXT = "png"
JPG_EXT = "jpg"
JPEG_EXT = "jpeg"
WEBP_EXT = "webp"
AVIF_EXT = "avif"

# ファイルパスの拡張子が一致するかどうか


def is_same_image_extension(file_path: str) -> bool:
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
    if output_format.lower() == PNG_EXT:
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        metadata_obj = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata_obj.add_text(key, value)
        image.save(output_path, format="PNG", pnginfo=metadata_obj,
                   quality=quality, lossless=lossless)
    elif output_format.lower() in (JPEG_EXT, JPG_EXT):
        if image.mode == "RGBA":
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
        image.save(output_path, format="JPEG", quality=quality,
                   optimize=True, exif=exif_bytes, lossless=lossless)
    elif output_format.lower() == WEBP_EXT:
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
        image.save(output_path, format="WEBP", quality=quality,
                   exif=exif_bytes, lossless=lossless)
    elif output_format.lower() == AVIF_EXT:
        image.encoderinfo = {}
        image.encoderinfo['alpha_premultiplied'] = False
        image.encoderinfo['autotiling'] = True
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
        image.save(output_path, format="AVIF", quality=quality,
                   exif=exif_bytes, lossless=lossless)

    else:
        raise ValueError(f"Invalid output format: {output_format}")


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

    # 画像ファイル単体の場合
    if is_same_image_extension(input_path):
        output_path = get_unique_filename(
            input_path, output_folder_path, output_format)
        try:
            convert_image((input_path, output_path, output_format,
                          quality, lossless, is_fill_transparenct, transparent_color))
        except Exception as e:
            raise ValueError(f"変換中にエラーが発生しました: {e}")
    else:
        files = [os.path.join(input_path, file) for file in os.listdir(
            input_path) if is_same_image_extension(file)]

        output_pathes = []
        for i, file in enumerate(files):
            path = get_unique_filename(
                file, output_folder_path, output_format, i+1)
            output_pathes.append(path)

        start_time = time.time()

        with ProcessPoolExecutor(max_workers=cpu_num) as executor:
            futures = []
            for file, output_path in zip(files, output_pathes):
                if file is None or output_path is None:
                    raise ValueError("入力フォルダパスまたは出力フォルダパスがありません")
                if not should_stop:
                    futures.append(
                        executor.submit(
                            convert_image,
                            (file, output_path, output_format, quality,
                                lossless, is_fill_transparenct, transparent_color)))
                else:
                    break

            try:
                for future in as_completed(futures):
                    if not should_stop:
                        future.result()
                    else:
                        executor.shutdown(wait=False)  # 実行中のタスクを強制終了
                        raise Exception("画像の変換を停止しました")
            except Exception as e:
                print(f"Task generated an exception: {e}")

                # Futureをキャンセル
                for future in futures:
                    if not future.running():
                        future.cancel()

                # futureの状態を確認
                for future in futures:
                    print(
                        f"running: {future.running()}, cancelled: {future.cancelled()}")

                # プロセスに終了要求
                for process in executor._processes.values():
                    process.terminate()

                gone, alive = psutil.wait_procs(
                    executor._processes.values(), timeout=3)

                for p in alive:
                    print("プロセスを強制終了しました", p)
                    p.kill()

        end_time = time.time()

        if not should_stop:
            print(f"Processing completed in {end_time - start_time} seconds.")


# スクリプトを停止するためのグローバル変数とロックオブジェクト
should_stop = False
stop_lock = threading.Lock()


def stop_script():
    global should_stop
    with stop_lock:
        should_stop = True


def exist_images(path):
    # 画像ファイル単体の場合
    if os.path.exists(path) and is_same_image_extension(path):
        return True

    # フォルダ内に画像ファイルが存在するかどうか
    for root, _, files in os.walk(path):
        for file in files:
            if is_same_image_extension(file):
                return True
    return False
