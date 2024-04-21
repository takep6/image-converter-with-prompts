import os
import sys

from PIL import Image, UnidentifiedImageError

"""
TODO: webpに変換できるがメタデータの埋め込みに失敗しているので要修正
"""


def convert_image(input_path, output_format):
    try:
        with Image.open(input_path) as img:
            metadata = img.info
            output_path = f"{os.path.splitext(input_path)[0]}.{output_format}"
            img.save(output_path, format=output_format, **metadata)
            print(f"変換完了: {output_path}")
    except UnidentifiedImageError:
        print(f"画像ファイルを開けませんでした: {input_path}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")


def convert_images_in_folder(folder_path, output_format):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                input_path = os.path.join(root, file)
                convert_image(input_path, output_format)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python convert_images.py <ファイル/フォルダ> <出力形式>")
    else:
        path = sys.argv[1]
        output_format = sys.argv[2]
        isdir = os.path.isdir(path)
        isfile = os.path.isfile(path)

        if isdir:
            convert_images_in_folder(path, output_format)
        elif isfile:
            convert_image(path, output_format)
