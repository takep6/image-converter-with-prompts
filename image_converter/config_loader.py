
import json
import os

import psutil


class ConfigLoader:
    # json keys
    INPUT_KEY = "input_path"
    OUTPUT_KEY = "output_path"
    EXT_KEY = "ext_path"
    COMP_RATIO_KEY = "comp_ratio"
    LOSSLESS_KEY = "lossless"
    Fill_TRANSPARENT_KEY = "fill_transparent"
    TRANSPARENT_COLOR_KEY = "transparent_color"
    CPU_NUM_KEY = "cpu_num"

    def __init__(self):
        # json filename
        self.assets_dir = f"{os.getcwd()}/assets"
        os.makedirs(self.assets_dir, exist_ok=True)
        self.datafile = os.path.join(self.assets_dir, "config.json")

        # init values
        self.init_input_path_val = ""
        self.init_output_path_val = ""
        self.init_ext_val = "webp"
        self.init_comp_ratio_val = 100
        self.init_lossless_val = False
        self.init_fill_transparent_val = False
        self.init_transparent_color = "#ffffff"
        self.init_cpu_num = psutil.cpu_count(logical=False)

        try:
            self.load()
        except FileNotFoundError:
            print("config.jsonのロードに失敗しました。初期値でアプリを開始します。")
            self.create()
            self.load()

    def load(self):
        with open(self.datafile, "r") as f:
            data = json.load(f)
            self.input_path_val = data[self.INPUT_KEY]
            self.output_path_val = data[self.OUTPUT_KEY]
            self.ext_val = data[self.EXT_KEY]
            self.comp_ratio_val = data[self.COMP_RATIO_KEY]
            self.lossless_val = data[self.LOSSLESS_KEY]
            self.fill_transparent_val = data[self.Fill_TRANSPARENT_KEY]
            self.transparent_color_val = data[self.TRANSPARENT_COLOR_KEY]
            self.cpu_num_val = data[self.CPU_NUM_KEY]

    def create(self):
        with open(self.datafile, "w") as f:
            new_data = {
                self.INPUT_KEY: self.init_input_path_val,
                self.OUTPUT_KEY: self.init_output_path_val,
                self.EXT_KEY: self.init_ext_val,
                self.COMP_RATIO_KEY: self.init_comp_ratio_val,
                self.LOSSLESS_KEY: self.init_lossless_val,
                self.Fill_TRANSPARENT_KEY: self.init_fill_transparent_val,
                self.TRANSPARENT_COLOR_KEY: self.init_transparent_color,
                self.CPU_NUM_KEY: self.init_cpu_num
            }
            json.dump(new_data, f, indent=4)

    def save(self, input_path, output_path, ext, comp_ratio, is_lossless, is_fill_transparent, transparent_color, cpu_num):
        os.makedirs(self.assets_dir, exist_ok=True)
        with open(self.datafile, "w") as f:
            new_data = {
                self.INPUT_KEY: input_path,
                self.OUTPUT_KEY: output_path,
                self.EXT_KEY: ext,
                self.COMP_RATIO_KEY: comp_ratio,
                self.LOSSLESS_KEY: is_lossless,
                self.Fill_TRANSPARENT_KEY: is_fill_transparent,
                self.TRANSPARENT_COLOR_KEY: transparent_color,
                self.CPU_NUM_KEY: cpu_num
            }
            json.dump(new_data, f, indent=4)
