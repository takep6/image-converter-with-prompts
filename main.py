import json
import os

import flet as ft
import psutil
from flet import (Card, Checkbox, Column, Container, Dropdown, ElevatedButton,
                  FilePicker, FilePickerResultEvent, Icon, MainAxisAlignment,
                  ProgressBar, Ref, Row, Slider, Switch, Text, TextButton,
                  TextField, alignment, colors, dropdown, icons)
from flet_contrib.color_picker import ColorPicker

import image_converter as converter

"""
TODO:
フォルダ内の全てのフォルダを変換する機能を実装する？
CPUを使いすぎない方法はある？->cpuの使用数で調節
巨大な画像が変換できるか、大量の画像でも問題なく完遂できるかチェック
スライダー作成・navigationdrawer作成・jsonへの保存設定・マルチプロセスのキル
"""


def main(page):
    # json keys
    INPUT_KEY = "input_path"
    OUTPUT_KEY = "output_path"
    EXT_KEY = "ext_path"
    COMP_RATIO_KEY = "comp_ratio"
    LOSSLESS_KEY = "lossless"
    Fill_TRANSPARENT_KEY = "fill_transparent"
    TRANSPARENT_COLOR_KEY = "transparent_color"
    THEME_KEY = "theme_mode"
    CPU_NUM_KEY = "cpu_num"

    assets_dir = f"{os.getcwd()}/assets"
    os.makedirs(assets_dir, exist_ok=True)
    # json filename
    datafile = os.path.join(assets_dir, "data.json")
    themefile = os.path.join(assets_dir, "theme.json")
    # test
    # datafile = f"{os.getcwd()}/data.json"
    # themefile = f"{os.getcwd()}/theme.json"

    # init values
    init_input_path_val = ""
    init_output_path_val = ""
    init_ext_val = "webp"
    init_comp_ratio_val = 100
    init_lossless_val = False
    init_fill_transparent_val = False
    init_transparent_color = "#ffffff"
    init_theme_val = "light"
    init_cpu_num = psutil.cpu_count(logical=False)
    max_cpu_num = psutil.cpu_count(logical=True)

    # create jsonfile
    if not os.path.exists(datafile):
        with open(datafile, "w") as f:
            new_data = {
                INPUT_KEY: init_input_path_val,
                OUTPUT_KEY: init_output_path_val,
                EXT_KEY: init_ext_val,
                COMP_RATIO_KEY: init_comp_ratio_val,
                LOSSLESS_KEY: init_lossless_val,
                Fill_TRANSPARENT_KEY: init_fill_transparent_val,
                TRANSPARENT_COLOR_KEY: init_transparent_color,
                CPU_NUM_KEY: init_cpu_num
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
            fill_transparent_val = data[Fill_TRANSPARENT_KEY]
            transparent_color_val = data[TRANSPARENT_COLOR_KEY]
            cpu_num_val = data[CPU_NUM_KEY]

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
        fill_transparent_val = init_fill_transparent_val
        transparent_color_val = init_transparent_color
        cpu_num_val = init_cpu_num

    # page settings
    page.title = "Image Converter with prompt"
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
    stop_btn = Ref[ElevatedButton]()
    is_fill_transparent = Ref[Checkbox]()
    cpu_num_slider = Ref[Slider]()
    cpu_num_text = Ref[Text]()

    # ColorPicker
    def open_color_picker(e):
        d.open = True
        page.update()

    color_picker = ColorPicker(color=transparent_color_val, width=300)
    transparent_color = Container(
        width=60, height=35, border_radius=5,
        bgcolor=transparent_color_val,
        on_click=open_color_picker)

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
        input_path.current.value = e.path if e.path \
            else input_path.current.value
        if input_path.current.value != "":
            input_path.current.bgcolor = colors.BACKGROUND
            input_path.current.error_text = ""
        input_path.current.update()

    def select_output_path(e: FilePickerResultEvent):
        output_path.current.value = e.path if e.path \
            else output_path.current.value
        if output_path.current.value != "":
            output_path.current.bgcolor = colors.BACKGROUND
            output_path.current.error_text = ""
        output_path.current.update()

    def select_input_filepath(e: FilePickerResultEvent):
        input_path.current.value = e.files[0].path \
            if e.files else input_path.current.value
        if input_path.current.value != "":
            input_path.current.bgcolor = colors.BACKGROUND
            input_path.current.error_text = ""
        input_path.current.update()

    pick_input_path_dialog = FilePicker(on_result=select_input_path)
    pick_output_path_dialog = FilePicker(on_result=select_output_path)
    pick_input_filepath_dialog = FilePicker(on_result=select_input_filepath)
    page.overlay.extend([
        pick_input_path_dialog,
        pick_output_path_dialog,
        pick_input_filepath_dialog
    ])

    # compression value
    def change_comp_ratio_label(ratio):
        if ratio <= 30:
            compression_ratio.current.label = "ファイルサイズ 小"
        elif ratio <= 70:
            compression_ratio.current.label = "ファイルサイズ 中"
        else:
            compression_ratio.current.label = "ファイルサイズ 大"

    def set_comp_ratio_to_text(ratio):
        compression_ratio_text.current.value = f"品質: {ratio} %"
        compression_ratio_text.current.update()

    def set_comp_ratio(ratio):
        compression_ratio.current.value = ratio

    def change_comp_ratio(e):
        ratio = int(e.control.value)
        set_comp_ratio(ratio)
        change_comp_ratio_label(ratio)
        set_comp_ratio_to_text(ratio)
        compression_ratio.current.update()

    # progress bar
    progress_bar = ProgressBar(width=600, color=colors.AMBER_400)

    # format value
    def switch_options_value(ext):
        if ext == "png":
            lossless.current.value = True
            lossless.current.disabled = True
            set_comp_ratio(100)
            set_comp_ratio_to_text(100)
            compression_ratio.current.disabled = True
            is_fill_transparent.current.disabled = False
        elif ext == "jpg":
            lossless.current.value = False
            lossless.current.disabled = True
            compression_ratio.current.disabled = False
            is_fill_transparent.current.value = True
            is_fill_transparent.current.disabled = True
        else:
            lossless.current.disabled = False
            compression_ratio.current.disabled = False
            is_fill_transparent.current.disabled = False

    def select_ext(e):
        switch_options_value(e.control.value)
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
    def save_to_json(input_dir, output_dir, file_ext, ratio,
                     is_lossless, is_fill_transparent, transparent_color, cpu_num):
        with open(datafile, "w") as f:
            update_data = {
                INPUT_KEY: input_dir,
                OUTPUT_KEY: output_dir,
                EXT_KEY: file_ext,
                COMP_RATIO_KEY: ratio,
                LOSSLESS_KEY: is_lossless,
                Fill_TRANSPARENT_KEY: is_fill_transparent,
                TRANSPARENT_COLOR_KEY: transparent_color,
                CPU_NUM_KEY: cpu_num
            }
            json.dump(update_data, f, indent=4)

    # toggle theme

    def toggle_textfield_border():
        border_color = colors.BLACK if page.theme_mode == "light" \
            else colors.BLUE_600
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

    def toggle_transparency(e):
        is_fill_transparent.current.value = e.control.value
        is_fill_transparent.current.update()

    # quit app
    def on_window_close(e):
        if e.data == "close":
            converter.stop_script()
            print("アプリケーションを終了します")

    page.on_window_event = on_window_close

    # set process num (cpu num)
    def set_cpu_num(num):
        cpu_num_slider.current.value = num
        cpu_num_slider.current.update()

    def update_cpu_text(num):
        cpu_num_text.current.value = f"プロセスの同時実行数: {num}"
        cpu_num_text.current.update()

    def change_cpu_num(e):
        num = int(e.control.value)
        set_cpu_num(num)
        update_cpu_text(num)

    # detailed configuration
    end_drawer = ft.NavigationDrawer(
        controls=[
            Container(
                padding=30, alignment=alignment.center,
                content=Row(
                    alignment=MainAxisAlignment.CENTER,
                    controls=[
                        Icon(icons.SETTINGS),
                        Text(value="詳細設定", size=24, weight=font_bold),
                    ])),
            ft.Divider(),
            Container(
                padding=20, alignment=alignment.center,
                content=Row(
                    alignment=MainAxisAlignment.CENTER,
                    controls=[
                        Text(
                            ref=cpu_num_text,
                            value=f"プロセスの同時実行数: {cpu_num_val}",
                            size=16, weight=font_bold),
                        Slider(
                            ref=cpu_num_slider,
                            min=1, max=max_cpu_num,
                            divisions=max_cpu_num-1, width=100,
                            value=cpu_num_val,
                            on_change=change_cpu_num
                        )
                    ])),
            Container(
                padding=20, alignment=alignment.center,
                on_click=toggle_theme,
                ink=True,
                content=Row(
                    alignment=MainAxisAlignment.CENTER,
                    controls=[
                        Icon(icons.DARK_MODE),
                        Text(value="テーマ", size=16, weight=font_bold)
                    ]
                ),
            ),
        ]
    )

    def show_end_drawer(e):
        page.show_end_drawer(end_drawer)

    page.floating_action_button = ft.FloatingActionButton(
        icon=icons.SETTINGS, on_click=show_end_drawer)

    # run
    def run_compression(e):
        # check input value
        is_input_path_empty = input_path.current.value == ""
        is_output_path_empty = output_path.current.value == ""

        if is_input_path_empty:
            input_path.current.error_text = "Input Pathにフォルダパスを入力してください"
            input_path.current.bgcolor = colors.RED_100
        else:
            input_path.current.error_text = ""
            input_path.current.bgcolor = colors.BACKGROUND

        if is_output_path_empty:
            output_path.current.error_text = "Output Pathにフォルダパスを入力してください"
            output_path.current.bgcolor = colors.RED_100
        else:
            output_path.current.error_text = ""
            output_path.current.bgcolor = colors.BACKGROUND

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
        is_fill_transparent_val = is_fill_transparent.current.value
        t_color = transparent_color.bgcolor
        cpu_num = cpu_num_slider.current.value

        # save json
        save_to_json(
            input_dir=input_path_val,
            output_dir=output_path_val,
            file_ext=file_ext,
            ratio=ratio,
            is_lossless=is_lossless,
            is_fill_transparent=is_fill_transparent_val,
            transparent_color=t_color,
            cpu_num=cpu_num
        )

        # log
        log_output.current.value = f"Input Path: {input_path_val}\n"
        log_output.current.value += f"Output Path: {output_path_val}\n"
        log_output.current.value += f"Format: *.{file_ext}\n"
        log_output.current.value += f"Process Num: {cpu_num}\n"
        log_output.current.value += f"Lossless: {is_lossless}\n"
        if not is_lossless:
            log_output.current.value += f"Quality: {ratio}%\n"
        if is_fill_transparent_val:
            log_output.current.value += f"Fill Color: {t_color}\n"

        # prevent double clicking
        run_btn.current.disabled = True
        stop_btn.current.disabled = False
        page.add(progress_bar)
        page.update()

        # Actual compression logic goes here
        try:
            os.makedirs(output_path_val, exist_ok=True)
            settings = (input_path_val, output_path_val,
                        file_ext, ratio, is_lossless,
                        is_fill_transparent_val, t_color, cpu_num)

            if converter.exist_images(input_path_val):
                converter.convert_images_in_folder(settings)
                log_output.current.value += "画像の変換が完了しました"
            else:
                log_output.current.value = "画像ファイルが存在しません"

        except Exception as e:
            log_output.current.value += "変換中にエラーが発生しました\n"
            log_output.current.value += str(e)
        finally:
            page.remove(progress_bar)
            run_btn.current.disabled = False
            stop_btn.current.disabled = True
            page.update()

    # stop
    def stop_compression(e):
        converter.stop_script()

    # page layout
    page.add(
        Column(
            width=800,
            controls=[
                Container(
                    alignment=alignment.center, padding=10,
                    content=Text(
                        value="画像圧縮変換ツール　アッシュくん",
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
                                    Text(
                                        "AI生成画像のプロンプトを残したまま画像ファイルの拡張子を変換します（アニメーションは非対応）"),
                                    Text(
                                        "ローカル版の画像のプロンプトのみ保存されます。NovelAIのプロンプトやその他のメタデータは保存されません"),
                                    Text("jpg, png, webp, avif形式に対応しています"),
                                ])),
                    )),
                Container(
                    padding=10,
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
                                                "jpeg", "jpg", "png", "webp", "avif"],
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
                            Container(
                                alignment=alignment.center_right,
                                height=25, margin=ft.Margin(0, 0, 30, 0),
                                content=TextButton(
                                    "出力フォルダを開く", on_click=open_output_dir)),
                        ])),

                Row(
                    alignment=MainAxisAlignment.SPACE_EVENLY,
                    controls=[
                        Card(
                            Container(
                                padding=20, width=350,
                                alignment=alignment.center,
                                content=Column(
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                    height=180,
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
                                                    value=ext_val,
                                                    options=[
                                                        dropdown.Option("jpg"),
                                                        dropdown.Option("png"),
                                                        dropdown.Option(
                                                            "webp"),
                                                        dropdown.Option(
                                                            "avif"),
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
                                            width=260,
                                            controls=[
                                                Text(
                                                    ref=compression_ratio_text,
                                                    value=f"品質: {comp_ratio_val} %",
                                                    width=120, size=16,
                                                    weight=font_bold),
                                                Slider(
                                                    ref=compression_ratio,
                                                    label="ファイルサイズ 大",
                                                    min=0, max=100,
                                                    value=comp_ratio_val,
                                                    width=140, divisions=20,
                                                    on_change=change_comp_ratio),
                                            ]),
                                    ]))),
                        Column(
                            controls=[
                                Card(
                                    Container(
                                        padding=20, width=350,
                                        alignment=alignment.center,
                                        content=Column([
                                            Row(
                                                alignment=MainAxisAlignment.START,
                                                width=250,
                                                controls=[
                                                    Text(
                                                        value="透過部分を塗りつぶす",
                                                        width=150, size=16,
                                                        weight=font_bold),
                                                    Checkbox(
                                                        ref=is_fill_transparent,
                                                        value=fill_transparent_val,
                                                        width=80,
                                                        on_change=toggle_transparency
                                                    ),
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
                                        ]),
                                    )),
                                Container(
                                    padding=20, alignment=alignment.center, content=Row(
                                        controls=[
                                            ElevatedButton(
                                                ref=run_btn,
                                                icon=icons.PLAY_ARROW,
                                                text="実行", width=200, height=60,
                                                on_click=run_compression),
                                            ElevatedButton(
                                                ref=stop_btn,
                                                icon=icons.STOP, text="停止",
                                                width=110, height=60,
                                                on_click=stop_compression)
                                        ]),
                                )


                            ]),
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
    switch_options_value(ext_val)
    stop_btn.current.disabled = True
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
