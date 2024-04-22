import os
import sys

import piexif
import piexif.helper
from PIL import Image, PngImagePlugin


def get_unique_filename(input_path, output_folder_path, output_format):
    basename = os.path.basename(input_path)
    filename = os.path.splitext(basename)[0]
    output_path = f"{output_folder_path}/{filename}.{output_format}"

    # ファイルが既に存在する場合は連番を付ける
    i = 1
    while os.path.exists(output_path):
        new_filename = f"{filename}_{i:03d}"
        output_path = f"{output_folder_path}/{new_filename}.{output_format}"
        i += 1

    return output_path


def convert_image(input_path, output_folder_path, output_format, quality, lossless=False):
    with Image.open(input_path) as image:
        # 出力先
        output_path = get_unique_filename(
            input_path, output_folder_path, output_format)

        # メタデータを取得
        param_dict = {}
        if input_path.lower().endswith("png"):
            param_dict = image.info
        elif input_path.lower().endswith(("jpg", "jpeg", "webp")):
            exif_dict = piexif.load(image.info["exif"])
            # 'Exif'セクションからUserCommentを取得
            user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
            # UserCommentを文字列に復元
            param_dict = {
                "parameters": piexif.helper.UserComment.load(user_comment)}

        # フォーマットごとにメタデータの保存の仕方が違う
        if output_format.lower() == 'png':
            use_metadata = False
            metadata = PngImagePlugin.PngInfo()
            for key, value in param_dict.items():
                if isinstance(key, str) and isinstance(value, str):
                    metadata.add_text(key, value)
                    use_metadata = True
            image.save(output_path, format="PNG", pnginfo=(
                metadata if use_metadata else None), quality=quality, lossless=lossless)

        elif output_format.lower() in ("jpg", "jpeg", "webp"):
            if image.mode == "RGBA":
                image = image.convert("RGB")
            parameters = param_dict.get('parameters', None)
            exif_bytes = piexif.dump({
                "Exif": {piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(parameters or "", encoding="unicode")}
            })

            if output_format.lower() in ("jpg", "jpeg"):
                image.save(output_path, format="JPEG",
                           exif=exif_bytes, quality=quality)
            else:
                image.save(output_path, format="WEBP",
                           exif=exif_bytes, quality=quality)

        else:
            raise Exception("Invalid image format")


def convert_images_in_folder(folder_path, output_path, output_format, quality, lossless=False):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                input_path = os.path.join(root, file)
                convert_image(input_path, output_path, output_format, quality)


if __name__ == "__main__":
    # if len(sys.argv) < 3:
    #     print("使用方法: python convert_images.py <ファイル/フォルダ> <出力形式>")
    # else:
    # input_path = sys.argv[1]
    # output_format = sys.argv[2]
    input_path = "./input"
    output_format = "jpg"
    output_path = "./output"
    quality = 100
    lossless = True
    isdir = os.path.isdir(input_path)
    isfile = os.path.isfile(input_path)

    os.makedirs(output_path, exist_ok=True)

    if isdir:
        convert_images_in_folder(
            input_path, output_path, output_format, quality, lossless)
    elif isfile:
        convert_image(input_path, output_path,
                      output_format, quality, lossless)
    else:
        raise Exception("File or Directory is Not Found.")
