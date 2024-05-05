import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import piexif
import piexif.helper
from PIL import Image, PngImagePlugin


def get_unique_filename(input_path, output_folder_path, output_format):
    basename = os.path.basename(input_path)
    filename, _ = os.path.splitext(basename)
    output_path = f"{output_folder_path}/{filename}.{output_format}"
    counter = 1
    while os.path.exists(output_path):
        output_path = f"{output_folder_path}/{filename}_{counter:03d}.{output_format}"
        counter += 1
    return output_path


def extract_metadata(image, input_path):
    metadata = {}
    if input_path.lower().endswith("png"):
        metadata = image.info
    elif input_path.lower().endswith(("jpg", "jpeg", "webp")):
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

    else:
        raise ValueError(f"Invalid output format: {output_format}")


def convert_image(settings):
    input_path, output_folder_path, output_format, quality, lossless, is_fill_transparenct, transparent_color = settings

    with Image.open(input_path) as image:
        output_path = get_unique_filename(
            input_path, output_folder_path, output_format)
        metadata = extract_metadata(image, input_path)
        save_with_metadata(image, output_path, output_format,
                           quality, metadata, lossless, is_fill_transparenct, transparent_color)


def convert_images_in_folder(settings):
    input_path, output_folder_path, output_format, quality, lossless, is_fill_transparenct, transparent_color = settings

    files = [os.path.join(input_path, file) for file in os.listdir(
        input_path) if file.endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    # タイム測定
    start_time = time.time()

    with ThreadPoolExecutor() as executor:
        # Submit tasks to the executor and get futures
        futures = [executor.submit(
            convert_image, (file, output_folder_path, output_format, quality, lossless, is_fill_transparenct, transparent_color)) for file in files]

        # Process completed tasks
        for future in as_completed(futures):
            try:
                _ = future.result()
            except Exception as e:
                print(f"Task generated an exception: {e}")

    end_time = time.time()
    print(f"Processing completed in {end_time - start_time} seconds.")


def exist_images_in_folder(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return True
    return False


def exist_image_path(image_path):
    return os.path.exists(image_path) and \
        image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
