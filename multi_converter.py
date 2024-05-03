import os
import time  # 実行時間測定のためにインポート
from concurrent.futures import (ProcessPoolExecutor, ThreadPoolExecutor,
                                as_completed)
from typing import Tuple

from PIL import Image

# def convert_image_to_jpg(args):
#     file_path, output_dir = args
#     if file_path.endswith('.png'):
#         img = Image.open(file_path)
#         basename = os.path.basename(file_path)
#         filename, _ = os.path.splitext(basename)
#         output_path = f"{output_dir}/{filename}.jpg"
#         img.convert('RGB').save(output_path, "JPEG")
#         # print(f"Converted {file_path} to {output_path}")


# def main():
#     # Directory containing PNG images to be converted
#     directory = "./input"
#     output_dir = "./output"
#     num_cores = os.cpu_count()
#     print(num_cores)
#     files = [os.path.join(directory, file) for file in os.listdir(
#         directory) if file.endswith('.png')]  # Get all files in the directory

#     start_time = time.time()  # 開始時刻を記録

#     # Use ThreadPoolExecutor for concurrent processing

#     with ThreadPoolExecutor() as executor:
#         executor.map(convert_image_to_jpg, [
#                      (file, output_dir) for file in files])

#     # for file in files:
#     #     convert_image_to_jpg((file, output_dir))

#     end_time = time.time()  # 終了時刻を記録

#     # 実行時間を表示
#     print(f"Processing completed in {end_time - start_time} seconds.")


# if __name__ == "__main__":
#     main()

# multi
"""
0.2596111297607422 seconds.
0.29680538177490234 seconds.
0.2655630111694336 seconds.
"""

# single
"""
0.9104440212249756 seconds.
0.9904038906097412 seconds.
0.8995227813720703 seconds.
"""


def convert_image_to_jpg(file_path_and_output_dir: Tuple[str, str]) -> str:
    """
    Convert a PNG image to JPG format.

    Args:
        file_path_and_output_dir (Tuple[str, str]): A tuple containing the file path of the PNG image and the output directory.

    Returns:
        str: A message indicating the success or failure of the conversion.
    """
    file_path, output_dir = file_path_and_output_dir

    try:
        if file_path.endswith('.png'):
            img = Image.open(file_path)
            basename = os.path.basename(file_path)
            filename, _ = os.path.splitext(basename)
            output_path = os.path.join(output_dir, f"{filename}.jpg")
            img.convert('RGB').save(output_path, "JPEG")
            return f"Converted {file_path} to {output_path}"
    except (IOError, ValueError) as e:
        return f"Error converting {file_path}: {e}"


def main():
    input_dir = "./input"
    output_dir = "./output"

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get a list of PNG files in the input directory
    png_files = [os.path.join(input_dir, file) for file in os.listdir(
        input_dir) if file.endswith('.png')]

    start_time = time.time()  # 開始時刻を記録

    with ProcessPoolExecutor() as executor:
        # Submit tasks to the executor and get futures
        futures = [executor.submit(
            convert_image_to_jpg, (file, output_dir)) for file in png_files]

        # Process completed tasks
        for future in as_completed(futures):
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"Task generated an exception: {e}")

    end_time = time.time()  # 終了時刻を記録

    # 実行時間を表示
    print(f"Processing completed in {end_time - start_time} seconds.")


if __name__ == "__main__":
    main()
