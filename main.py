import json
import os

import flet as ft
from flet import (Card, Column, Container, Dropdown, ElevatedButton,
                  FilePicker, FilePickerResultEvent, Icon, MainAxisAlignment,
                  ProgressBar, Ref, Row, Slider, Switch, Text, TextButton,
                  TextField, alignment, colors, dropdown, icons)
from flet_contrib.color_picker import ColorPicker

import image_converter as converter

"""
TODO:
dpi、ビット数など画像データが問題なく変換できているかチェック
巨大な画像が変換できるか、大量の画像でも問題なく完遂できるかチェック
"""


def main(page):
    # json keys
    INPUT_KEY = "input_path"
    OUTPUT_KEY = "output_path"
    EXT_KEY = "ext_path"
    COMP_RATIO_KEY = "comp_ratio"
    LOSSLESS_KEY = "lossless"
    TRANSPARENT_KEY = "transparent_color"
    THEME_KEY = "theme_mode"

    # json filename
    datafile = "data.json"
    themefile = "theme.json"

    # init values
    init_input_path_val = ""
    init_output_path_val = ""
    init_ext_val = "webp"
    init_comp_ratio_val = 100
    init_lossless_val = False
    init_transparent_color = "#ffffff"
    init_theme_val = "light"

    # create jsonfile
    if not os.path.exists(datafile):
        with open(datafile, "w") as f:
            new_data = {
                INPUT_KEY: init_input_path_val,
                OUTPUT_KEY: init_output_path_val,
                EXT_KEY: init_ext_val,
                COMP_RATIO_KEY: init_comp_ratio_val,
                LOSSLESS_KEY: init_lossless_val,
                TRANSPARENT_KEY: init_transparent_color
            }
            json.dump(new_data, f, indent=4)

    if not os.path.exists(themefile):
        with open(themefile, "w") as f:
            new_theme = {
                THEME_KEY: init_theme_val
            }
            json.dump(new_theme, f, indent=4)

    # initialize values
    try:
        with open(datafile, "r")as f:
            data = json.load(f)
            input_path_val = data[INPUT_KEY]
            output_path_val = data[OUTPUT_KEY]
            ext_val = data[EXT_KEY]
            comp_ratio_val = data[COMP_RATIO_KEY]
            lossless_val = data[LOSSLESS_KEY]
            transparent_color_val = data[TRANSPARENT_KEY]

        with open(themefile, "r")as f:
            data = json.load(f)
            theme_val = data[THEME_KEY]

    except Exception as e:
        print(e, "jsonデータのロードに失敗しました。初期値でアプリを開始します。")
        input_path_val = init_input_path_val
        output_path_val = init_output_path_val
        ext_val = init_ext_val
        comp_ratio_val = init_comp_ratio_val
        lossless_val = init_lossless_val
        theme_val = init_theme_val
        transparent_color_val = init_transparent_color

    # page settings
    page.title = "Image Format Converter"
    page.theme_mode = theme_val
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 30
    page.window_width = 800
    page.window_height = 1000

    # text style
    font_bold = ft.FontWeight.BOLD

    # Control Ref
    input_path = Ref[TextField]()
    output_path = Ref[TextField]()
    file_exts_dropdown = Ref[Dropdown]()
    compression_ratio = Ref[Slider]()
    compression_ratio_text = Ref[Text]()
    lossless = Ref[Switch]()
    log_output = Ref[TextField]()
    run_btn = Ref[ElevatedButton]()

    # ColorPicker
    def open_color_picker(e):
        d.open = True
        page.update()

    color_picker = ColorPicker(color=transparent_color_val, width=300)
    transparent_color = Container(
        width=60, height=35, border_radius=5, bgcolor=transparent_color_val, on_click=open_color_picker)

    def change_color(e):
        transparent_color.bgcolor = color_picker.color
        d.open = False
        page.update()

    def close_dialog(e):
        d.open = False
        d.update()

    d = ft.AlertDialog(
        content=color_picker,
        actions=[
            ft.TextButton("OK", on_click=change_color),
            ft.TextButton("Cancel", on_click=close_dialog),
        ],
        actions_alignment=MainAxisAlignment.END,
    )
    page.dialog = d

    # FilePicker
    def select_input_path(e: FilePickerResultEvent):
        input_path.current.value = e.path if e.path else input_path.current.value
        if input_path.current.value != "":
            input_path.current.bgcolor = colors.BACKGROUND
            input_path.current.error_text = ""
            page.client_storage.set(INPUT_KEY, input_path.current.value)
        input_path.current.update()

    def select_output_path(e: FilePickerResultEvent):
        output_path.current.value = e.path if e.path else output_path.current.value
        if output_path.current.value != "":
            output_path.current.bgcolor = colors.BACKGROUND
            output_path.current.error_text = ""
            page.client_storage.set(OUTPUT_KEY, output_path.current.value)
        output_path.current.update()

    def select_input_filepath(e: FilePickerResultEvent):
        input_path.current.value = e.files[0].path if e.files else input_path.current.value
        if input_path.current.value != "":
            input_path.current.bgcolor = colors.BACKGROUND
            input_path.current.error_text = ""
            page.client_storage.set(INPUT_KEY, input_path.current.value)
        input_path.current.update()

    pick_input_path_dialog = FilePicker(on_result=select_input_path)
    pick_output_path_dialog = FilePicker(on_result=select_output_path)
    pick_input_filepath_dialog = FilePicker(on_result=select_input_filepath)
    page.overlay.extend(
        [pick_input_path_dialog, pick_output_path_dialog, pick_input_filepath_dialog]
    )

    # compression value
    def set_comp_ratio_val(e):
        comp_val = int(e.control.value)
        compression_ratio.current.value = comp_val
        compression_ratio_text.current.value = f"圧縮率: {comp_val} %"
        if comp_val <= 30:
            compression_ratio.current.label = "ファイルサイズ 小"
        elif comp_val <= 70:
            compression_ratio.current.label = "ファイルサイズ 中"
        else:
            compression_ratio.current.label = "ファイルサイズ 大"
        page.update()

    progress_bar = ProgressBar(width=600, color=colors.AMBER_400)

    # format value
    def switch_settings(ext):
        if ext == "png":
            lossless.current.disabled = True
            compression_ratio.current.disabled = True
            transparent_color.disabled = True
        elif ext == "jpg":
            lossless.current.disabled = True
            compression_ratio.current.disabled = False
            transparent_color.disabled = False
        else:
            lossless.current.disabled = False
            compression_ratio.current.disabled = False
            transparent_color.disabled = False

    def select_ext(e):
        switch_settings(e.control.value)
        page.update()

    def open_output_dir(e):
        # OS によって適切なコマンドを使ってフォルダを開く
        if os.name == 'nt':  # Windows の場合
            os.system(f'explorer "{output_path.current.value}"')
        elif os.name == 'posix':  # macOS や Linux の場合
            os.system(f'open "{output_path.current.value}"')
        else:
            print("この OS はサポートされていません。")

    # save
    def save_to_json(input_dir, output_dir, file_ext, ratio, is_lossless, transparent_color):
        with open(datafile, "w") as f:
            update_data = {
                INPUT_KEY: input_dir,
                OUTPUT_KEY: output_dir,
                EXT_KEY: file_ext,
                COMP_RATIO_KEY: ratio,
                LOSSLESS_KEY: is_lossless,
                TRANSPARENT_KEY: transparent_color
            }
            json.dump(update_data, f, indent=4)

    # run
    def run_compression(e):
        # check input value
        is_input_path_empty = input_path.current.value == ""
        is_output_path_empty = output_path.current.value == ""

        if is_input_path_empty:
            input_path.current.error_text = "Input Pathにフォルダパスを入力してください"
            input_path.current.bgcolor = ft.colors.RED_100
        if is_output_path_empty:
            output_path.current.error_text = "Output Pathにフォルダパスを入力してください"
            output_path.current.bgcolor = ft.colors.RED_100
        if is_input_path_empty or is_output_path_empty:
            page.update()
            return

        input_path_val = input_path.current.value
        output_path_val = output_path.current.value
        file_ext = file_exts_dropdown.current.value.lower()
        if file_ext == "png":
            is_lossless = True
        elif file_ext == "jpg":
            is_lossless = False
        else:
            is_lossless = lossless.current.value
        ratio = 100 if is_lossless else int(compression_ratio.current.value)
        t_color = transparent_color.bgcolor

        # save json
        save_to_json(
            input_dir=input_path_val,
            output_dir=output_path_val,
            file_ext=file_ext,
            ratio=ratio,
            is_lossless=is_lossless,
            transparent_color=t_color
        )

        # log
        log_output.current.value = f"Input Path: {input_path_val}\n"
        log_output.current.value += f"Output Path: {output_path_val}\n"
        log_output.current.value += f"Format: *.{file_ext}\n"
        if is_lossless:
            log_output.current.value += f"Lossless: {is_lossless}\n"
        else:
            log_output.current.value += f"Compression Ratio: {ratio}%\n"
            log_output.current.value += f"Fill Color: {t_color}\n"

        # prevent double clicking
        run_btn.current.disabled = True
        page.add(progress_bar)
        page.update()

        # Actual compression logic goes here
        try:
            # 画像ファイル単体を処理
            if converter.exist_image_path(input_path_val):
                converter.convert_image(
                    input_path=input_path_val,
                    output_folder_path=output_path_val,
                    output_format=file_ext,
                    quality=ratio,
                    lossless=is_lossless,
                    transparent_color=t_color
                )
                log_output.current.value += "画像の変換が完了しました"
            # フォルダ内の画像を全て処理
            elif converter.exist_images_in_folder(input_path_val):
                converter.convert_images_in_folder(
                    folder_path=input_path_val,
                    output_path=output_path_val,
                    output_format=file_ext,
                    quality=ratio,
                    lossless=is_lossless,
                    transparent_color=t_color
                )
                log_output.current.value += "画像の変換が完了しました"
            else:
                log_output.current.value = "画像ファイルが存在しません"

        except Exception as e:
            log_output.current.value += "変換中にエラーが発生しました"
            log_output.current.value += str(e)
        finally:
            page.remove(progress_bar)
            run_btn.current.disabled = False
            page.update()

    # toggle theme
    def toggle_textfield_border():
        border_color = colors.BLACK if page.theme_mode == "light" else colors.BLUE_600
        input_path.current.border_color = border_color
        output_path.current.border_color = border_color
        log_output.current.border_color = border_color

    def toggle_theme(e):
        page.theme_mode = "light" if page.theme_mode == "dark" else "dark"
        toggle_textfield_border()
        page.update()

        # save to json
        theme = "light" if page.theme_mode == "light" else "dark"
        with open(themefile, "w") as f:
            update_theme = {
                THEME_KEY: theme
            }
            json.dump(update_theme, f, indent=4)

    page.floating_action_button = ft.FloatingActionButton(
        icon=icons.DARK_MODE, on_click=toggle_theme)

    # page layout
    page.add(
        Column(
            width=800,
            controls=[
                Container(
                    alignment=alignment.center, padding=20,
                    content=Text(
                        value="画像圧縮変換ツール　アッシュ君",
                        size=40, weight=font_bold
                    )),
                Container(
                    alignment=alignment.center,
                    content=Card(
                        margin=10,
                        content=Container(
                            padding=20,
                            content=Column(
                                controls=[
                                    Text("AI生成画像のプロンプトを残したまま画像ファイルの拡張子を変換します"),
                                    Text("入力・出力ファイル形式はjpg, png, webpのみ対応")
                                ])),
                    )),
                Container(
                    padding=20,
                    content=Column(
                        controls=[
                            Row(
                                alignment=MainAxisAlignment.CENTER,
                                controls=[
                                    TextField(
                                        ref=input_path,
                                        label="入力フォルダパス",
                                        value=input_path_val, width=500),
                                    ElevatedButton(
                                        content=Icon(icons.FOLDER_OPEN),
                                        width=70, height=45,
                                        on_click=lambda _: pick_input_path_dialog.get_directory_path()),
                                    ElevatedButton(
                                        content=Icon(icons.IMAGE),
                                        width=70, height=45,
                                        on_click=lambda _: pick_input_filepath_dialog.pick_files(
                                            allow_multiple=True,
                                            file_type=ft.FilePickerFileType.IMAGE,
                                            allowed_extensions=[
                                                "jpeg", "jpg", "png", "webp"],
                                        )),
                                ]),
                            Row(
                                alignment=MainAxisAlignment.CENTER,
                                controls=[
                                    TextField(
                                        ref=output_path,
                                        label="出力フォルダパス",
                                        value=output_path_val, width=500),
                                    ElevatedButton(
                                        content=Icon(icons.FOLDER_OPEN),
                                        width=70, height=45,
                                        on_click=lambda _: pick_output_path_dialog.get_directory_path()),
                                    Container(
                                        width=70, height=45,
                                    ),
                                ]),
                        ])),
                Container(
                    alignment=alignment.center_right,
                    height=30, margin=ft.Margin(0, 0, 50, 0),
                    content=TextButton(
                        "出力フォルダを開く", on_click=open_output_dir)),
                Row(
                    alignment=MainAxisAlignment.SPACE_EVENLY,
                    controls=[
                        Card(
                            Container(
                                padding=20, width=300,
                                content=Column(
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                    height=200,
                                    controls=[
                                        Row(
                                            alignment=MainAxisAlignment.START,
                                            width=250,
                                            controls=[
                                                Text(
                                                    value="変換後の拡張子",
                                                    width=150, size=16,
                                                    weight=font_bold),
                                                Dropdown(
                                                    ref=file_exts_dropdown,
                                                    label="Format",
                                                    value=ext_val,
                                                    options=[
                                                        dropdown.Option("jpg"),
                                                        dropdown.Option("png"),
                                                        dropdown.Option(
                                                            "webp"),
                                                    ],
                                                    width=80,
                                                    on_change=select_ext
                                                ),
                                            ]),
                                        Row(
                                            alignment=MainAxisAlignment.START,
                                            width=250,
                                            controls=[
                                                Text(
                                                    value="可逆圧縮",
                                                    width=160, size=16,
                                                    weight=font_bold),
                                                Switch(ref=lossless,
                                                       value=lossless_val),
                                            ]),
                                        Row(
                                            alignment=MainAxisAlignment.START,
                                            width=250,
                                            controls=[
                                                Text(
                                                    ref=compression_ratio_text,
                                                    value=f"圧縮率: {comp_ratio_val} %",
                                                    width=120, size=16,
                                                    weight=font_bold),
                                                Slider(
                                                    ref=compression_ratio,
                                                    label="ファイルサイズ 大",
                                                    min=0, max=100,
                                                    value=comp_ratio_val,
                                                    width=150, divisions=20,
                                                    on_change=set_comp_ratio_val),
                                            ]),
                                        Row(
                                            alignment=MainAxisAlignment.START,
                                            width=250,
                                            controls=[
                                                Text(
                                                    value="透過部分の色",
                                                    width=160, size=16,
                                                    weight=font_bold),
                                                transparent_color,
                                            ]),
                                    ]))),
                        Container(
                            padding=20,
                            content=Column([
                                ElevatedButton(
                                    ref=run_btn,
                                    text="実行", width=180, height=150,
                                    on_click=run_compression)
                            ])),
                    ]),
                Column(
                    scroll=ft.ScrollMode.ALWAYS,
                    height=200,
                    controls=[
                        Container(
                            alignment=alignment.center,
                            padding=20,
                            content=TextField(
                                ref=log_output,
                                label="ログ", value="-",
                                multiline=True, read_only=True, width=600)
                        ),
                    ]),
            ])
    ),

    # 関数で初期化したい場合は、page.add()した後でないと実行できないので注意
    toggle_textfield_border()
    switch_settings(ext_val)
    page.update()


ft.app(target=main)
