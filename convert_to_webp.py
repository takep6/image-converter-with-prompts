# import os
# import sys

# import piexif
# import piexif.helper
# from PIL import Image, PngImagePlugin


# def get_unique_filename(input_path, output_folder_path, output_format):
#     basename = os.path.basename(input_path)
#     filename = os.path.splitext(basename)[0]
#     output_path = f"{output_folder_path}/{filename}.{output_format}"

#     # ファイルが既に存在する場合は連番を付ける
#     i = 1
#     while os.path.exists(output_path):
#         new_filename = f"{filename}_{i:03d}"
#         output_path = f"{output_folder_path}/{new_filename}.{output_format}"
#         i += 1

#     return output_path


# def convert_image(input_path, output_folder_path, output_format, quality, lossless=False):
#     with Image.open(input_path) as image:
#         # 出力先
#         output_path = get_unique_filename(
#             input_path, output_folder_path, output_format)

#         # メタデータを取得
#         param_dict = {}
#         if input_path.lower().endswith("png"):
#             param_dict = image.info
#         elif input_path.lower().endswith(("jpg", "jpeg", "webp")):
#             if "exif" in image.info.keys():
#                 exif_dict = piexif.load(image.info["exif"])
#                 if piexif.ExifIFD.UserComment in exif_dict["Exif"].keys():
#                     # 'Exif'セクションからUserCommentを取得
#                     user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
#                     # UserCommentを文字列に復元
#                     param_dict = {
#                         "parameters": piexif.helper.UserComment.load(user_comment)}

#                 # フォーマットごとにメタデータの保存の仕方が違う
#         if output_format.lower() == 'png':
#             use_metadata = False
#             metadata = PngImagePlugin.PngInfo()
#             for key, value in param_dict.items():
#                 if isinstance(key, str) and isinstance(value, str):
#                     metadata.add_text(key, value)
#                     use_metadata = True
#             image.save(output_path, format="PNG", pnginfo=(
#                 metadata if use_metadata else None), quality=quality, lossless=lossless)

#         elif output_format.lower() in ("jpg", "jpeg", "webp"):
#             if image.mode == "RGBA":
#                 image = image.convert("RGB")
#             parameters = param_dict.get('parameters', None)
#             exif_bytes = piexif.dump({
#                 "Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(parameters or "", encoding="unicode")}
#             })
#             print(exif_bytes)

#             if output_format.lower() in ("jpg", "jpeg"):
#                 image.save(output_path, format="jpeg",
#                            quality=int(quality), optimize=True, exif=exif_bytes, lossless=lossless)
#             else:
#                 image.save(output_path, format="WEBP",
#                            exif=exif_bytes, quality=quality, lossless=lossless)

#         else:
#             raise Exception("Invalid image format")


# def convert_images_in_folder(folder_path, output_path, output_format, quality, lossless=False):
#     # 出力フォルダが存在しなければ作成する
#     os.makedirs(output_path, exist_ok=True)

#     for root, dirs, files in os.walk(folder_path):
#         for file in files:
#             if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
#                 input_path = os.path.join(root, file)
#                 convert_image(input_path, output_path,
#                               output_format, quality, lossless)


# if __name__ == "__main__":
#     # テスト用
#     input_path = "./input"
#     output_format = "jpg"
#     output_path = "./output"
#     quality = 100
#     lossless = True
#     isdir = os.path.isdir(input_path)
#     isfile = os.path.isfile(input_path)

#     if isdir:
#         convert_images_in_folder(
#             input_path, output_path, output_format, quality, lossless)
#     elif isfile:
#         convert_image(input_path, output_path,
#                       output_format, quality, lossless)
#     else:
#         raise Exception("File or Directory is Not Found.")


import os

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


def save_with_metadata(image, output_path, output_format, quality, metadata, lossless=False):
    if output_format.lower() == "png":
        metadata_obj = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata_obj.add_text(key, value)
        image.save(output_path, format="PNG", pnginfo=metadata_obj,
                   quality=quality, lossless=lossless)
    elif output_format.lower() in ("jpg", "jpeg", "webp"):
        if image.mode == "RGBA":
            image = image.convert("RGB")
        exif_bytes = piexif.dump({"Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
            metadata.get("parameters", ""), encoding="unicode")}})
        if output_format.lower() in ("jpg", "jpeg"):
            image.save(output_path, format="JPEG", quality=quality,
                       optimize=True, exif=exif_bytes, lossless=lossless)
        else:
            image.save(output_path, format="WEBP", quality=quality,
                       exif=exif_bytes, lossless=lossless)
    else:
        raise ValueError(f"Invalid output format: {output_format}")


def convert_image(input_path, output_folder_path, output_format, quality, lossless=False):
    with Image.open(input_path) as image:
        output_path = get_unique_filename(
            input_path, output_folder_path, output_format)
        metadata = extract_metadata(image, input_path)
        save_with_metadata(image, output_path, output_format,
                           quality, metadata, lossless)


def convert_images_in_folder(folder_path, output_path, output_format, quality, lossless=False):
    os.makedirs(output_path, exist_ok=True)
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                input_path = os.path.join(root, file)
                convert_image(input_path, output_path,
                              output_format, quality, lossless)
