import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import piexif
import piexif.helper
import pillow_avif
import psutil
from PIL import Image, PngImagePlugin


def get_unique_filename(input_path, output_folder_path, output_format, counter=0):
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


def extract_metadata(image, input_path):
    metadata = {}
    if input_path.lower().endswith("png"):
        metadata = image.info
    elif input_path.lower().endswith(("jpg", "jpeg", "webp", "avif")):
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
    if output_format.lower() == "png":
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        metadata_obj = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata_obj.add_text(key, value)
        image.save(output_path, format="PNG", pnginfo=metadata_obj,
                   quality=quality, lossless=lossless)
    elif output_format.lower() in ("jpg", "jpeg"):
        if image.mode == "RGBA":
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
        image.save(output_path, format="JPEG", quality=quality,
                   optimize=True, exif=exif_bytes, lossless=lossless)
    elif output_format.lower() in ("webp"):
        if is_fill_transparenct:
            image = convert_with_transparent_color(image, transparent_color)
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
        image.save(output_path, format="WEBP", quality=quality,
                   exif=exif_bytes, lossless=lossless)
    elif output_format.lower() in ("avif"):
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
    cpu_num = psutil.cpu_count(logical=False)

    input_path, output_folder_path, output_format, quality, lossless, is_fill_transparenct, transparent_color = settings

    # 画像ファイル単体の場合
    if output_folder_path.endswith(('.png', '.jpg', '.jpeg', '.webp', 'avif')):
        output_path = get_unique_filename(
            input_path, output_folder_path, output_format)
        convert_image((input_path, output_path, output_format,
                      quality, lossless, is_fill_transparenct, transparent_color))
    else:

        files = [os.path.join(input_path, file) for file in os.listdir(
            input_path) if file.endswith(('.png', '.jpg', '.jpeg', '.webp', 'avif'))]

        output_pathes = []
        for i, file in enumerate(files):
            path = get_unique_filename(
                file, output_folder_path, output_format, i+1)
            output_pathes.append(path)

        start_time = time.time()

        with ProcessPoolExecutor(max_workers=cpu_num) as executor:
            futures = []
            for file, output_path in zip(files, output_pathes):
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
                        _ = future.result()
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
                processes = executor._processes.values()
                for process in processes:
                    process.terminate()

                gone, alive = psutil.wait_procs(
                    executor._processes.values(), timeout=5)
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


def exist_images_in_folder(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', 'avif')):
                return True
    return False


def exist_image_path(image_path):
    return os.path.exists(image_path) and \
        image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', 'avif'))
