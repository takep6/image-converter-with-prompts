
import json
import os


class ThemeLoader:
    # json keys
    THEME_KEY = "theme_mode"

    def __init__(self):
        # json filename and path
        self.assets_dir = f"{os.getcwd()}/assets"
        self.datafile = os.path.join(self.assets_dir, "theme.json")
        os.makedirs(self.assets_dir, exist_ok=True)

        # init values
        self.init_theme = "light"

        if not os.path.exists(self.datafile):
            self.create()

        try:
            self.load()
        except FileNotFoundError:
            print("theme.jsonのロードに失敗しました。初期値でアプリを開始します。")
            self.create()
            self.load()

    def load(self):
        with open(self.datafile, "r") as f:
            data = json.load(f)
            self.theme = data[self.THEME_KEY]

    def write(self, theme):
        try:
            os.makedirs(self.assets_dir, exist_ok=True)
            with open(self.datafile, "w") as f:
                new_data = {
                    self.THEME_KEY: theme
                }
                json.dump(new_data, f, indent=4)
        except Exception as e:
            print(f"theme.jsonの保存に失敗しました。\n{e}")

    def create(self):
        self.write(self.init_theme)

    def save(self, theme):
        try:
            self.write(theme)
        except Exception as e:
            print("theme.jsonの保存に失敗しました。新しくtheme.jsonファイルを作成します。")
            os.path.exists(self.datafile, exist_ok=True)
            self.create()
            self.write(theme)
