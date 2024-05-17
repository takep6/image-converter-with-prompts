
import json
import os

import psutil


class ConfigLoader:
    # json keys
    INPUT_KEY = "input_path"
    OUTPUT_KEY = "output_path"
    IS_CONVERT_SUBFOLDERS = "is_convert_subfolders"
    EXT_KEY = "ext_path"
    QUALITY_KEY = "quality"
    LOSSLESS_KEY = "lossless"
    IS_Fill_COLOR_KEY = "is_fill_color"
    FILL_COLOR_KEY = "fill_color"
    CPU_NUM_KEY = "cpu_num"

    def __init__(self):
        # json filename
        self.assets_dir = f"{os.getcwd()}/assets"
        self.datafile = os.path.join(self.assets_dir, "config.json")
        os.makedirs(self.assets_dir, exist_ok=True)

        # init values
        self.init_input_path = ""
        self.init_output_path = ""
        self.init_is_convert_subfolders = False
        self.init_ext = "webp"
        self.init_quality = 100
        self.init_lossless = False
        self.init_is_fill_color = False
        self.init_fill_color = "#ffffff"
        self.init_cpu_num = psutil.cpu_count(logical=False)

        if not os.path.exists(self.datafile):
            self.create()

        try:
            self.load()
        except FileNotFoundError:
            print("config.jsonのロードに失敗しました。初期値でアプリを開始します。")
            self.create()
            self.load()

    def load(self):
        with open(self.datafile, "r") as f:
            data = json.load(f)
            self.input_path = data[self.INPUT_KEY]
            self.output_path = data[self.OUTPUT_KEY]
            self.is_convert_subfolders = data[self.IS_CONVERT_SUBFOLDERS]
            self.ext = data[self.EXT_KEY]
            self.quality = data[self.QUALITY_KEY]
            self.lossless = data[self.LOSSLESS_KEY]
            self.is_fill_color = data[self.IS_Fill_COLOR_KEY]
            self.fill_color = data[self.FILL_COLOR_KEY]
            self.cpu_num = data[self.CPU_NUM_KEY]

    def write(self, input_path, output_path, is_convert_subfolders, ext, quality, is_lossless, is_fill_color, fill_color, cpu_num):
        with open(self.datafile, "w") as f:
            new_data = {
                self.INPUT_KEY: input_path,
                self.OUTPUT_KEY: output_path,
                self.IS_CONVERT_SUBFOLDERS: is_convert_subfolders,
                self.EXT_KEY: ext,
                self.QUALITY_KEY: quality,
                self.LOSSLESS_KEY: is_lossless,
                self.IS_Fill_COLOR_KEY: is_fill_color,
                self.FILL_COLOR_KEY: fill_color,
                self.CPU_NUM_KEY: cpu_num
            }
            json.dump(new_data, f, indent=4)

    def create(self):
        self.write(
            self.init_input_path,
            self.init_output_path,
            self.init_is_convert_subfolders,
            self.init_ext,
            self.init_quality,
            self.init_lossless,
            self.init_is_fill_color,
            self.init_fill_color,
            self.init_cpu_num)

    def save(self, input_path, output_path, is_convert_subfolders, ext, quality,
             is_lossless, is_fill_color, fill_color, cpu_num):
        try:
            self.write(
                input_path,
                output_path,
                is_convert_subfolders,
                ext,
                quality,
                is_lossless,
                is_fill_color,
                fill_color,
                cpu_num)
        except Exception as e:
            print("config.jsonの保存に失敗しました。新しくconfig.jsonファイルを作成します。")
            os.path.exists(self.datafile, exist_ok=True)
            self.create()
            self.write(
                input_path,
                output_path,
                is_convert_subfolders,
                ext,
                quality,
                is_lossless,
                is_fill_color,
                fill_color, cpu_num)
