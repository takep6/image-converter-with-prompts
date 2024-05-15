import os
import re
import time

import flet as ft
import psutil
from flet import (Card, Checkbox, Column, Container, Dropdown, ElevatedButton,
                  FilePicker, FilePickerResultEvent, Icon, MainAxisAlignment,
                  ProgressBar, Ref, Row, Slider, Switch, Text, TextButton,
                  TextField, alignment, colors, dropdown, icons)
from flet_contrib.color_picker import ColorPicker

import image_converter.const as exts
import image_converter.image_converter as converter
from image_converter.config_loader import ConfigLoader
from image_converter.theme_loader import ThemeLoader


def main(page):
    # variables
    font_bold = ft.FontWeight.BOLD
    is_running_process = False
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    config = ConfigLoader()
    theme = ThemeLoader()

    # page settings
    page.title = "Image Converter with prompts"
    page.theme_mode = theme.theme_val
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 30
    page.window_width = 800
    page.window_height = 1000
    max_cpu_num = psutil.cpu_count(logical=True)

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
        page.dialog = color_dialog
        color_dialog.open = True
        page.update()

    color_picker = ColorPicker(color=config.transparent_color_val, width=300)
    transparent_color = Container(
        width=60, height=35, border_radius=5,
        bgcolor=config.transparent_color_val,
        on_click=open_color_picker)

    def change_color(e):
        transparent_color.bgcolor = color_picker.color
        color_dialog.open = False
        page.update()

    def close_dialog(e):
        color_dialog.open = False
        color_dialog.update()

    color_dialog = ft.AlertDialog(
        content=color_picker,
        actions=[
            ft.TextButton("決定", on_click=change_color),
            ft.TextButton("キャンセル", on_click=close_dialog),
        ],
        actions_alignment=MainAxisAlignment.END,
    )

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
        if ext == exts.PNG_EXT:
            lossless.current.value = True
            lossless.current.disabled = True
            set_comp_ratio(100)
            set_comp_ratio_to_text(100)
            compression_ratio.current.disabled = True
            is_fill_transparent.current.disabled = False
        elif ext == exts.JPG_EXT:
            lossless.current.value = False
            lossless.current.disabled = True
            compression_ratio.current.disabled = False
            is_fill_transparent.current.value = True
            is_fill_transparent.current.disabled = True
        elif ext == exts.AVIF_EXT:
            lossless.current.value = False
            lossless.current.disabled = True
            compression_ratio.current.disabled = False
            is_fill_transparent.current.disabled = False
        else:
            lossless.current.disabled = False
            compression_ratio.current.disabled = False
            is_fill_transparent.current.disabled = False

    def select_ext(e):
        switch_options_value(e.control.value)
        page.update()

    def open_input_dir(e):
        # ファイルかフォルダかを判別
        path = input_path.current.value
        path = os.path.dirname(path) if os.path.isfile(path) else path
        open_dir(path)

    def open_output_dir(e):
        open_dir(output_path.current.value)

    def open_dir(path):
        # OS によって適切なコマンドを使ってフォルダを開く
        if os.name == 'nt':  # Windows の場合
            os.system(f'explorer "{path}"')
        elif os.name == 'posix':  # macOS や Linux の場合
            os.system(f'open "{path}"')
        else:
            print("この OS はサポートされていません。")

    # toggle theme

    def toggle_textfield_border():
        border_color = colors.BLACK if page.theme_mode == LIGHT_THEME \
            else colors.BLUE_600
        input_path.current.border_color = border_color
        output_path.current.border_color = border_color
        log_output.current.border_color = border_color

    def toggle_theme(e):
        page.theme_mode = LIGHT_THEME if page.theme_mode == DARK_THEME \
            else DARK_THEME
        toggle_textfield_border()
        theme.save(page.theme_mode)
        page.update()

    def toggle_transparency(e):
        is_fill_transparent.current.value = e.control.value
        is_fill_transparent.current.update()

    # quit app
    def close_quit_dialog(e):
        quit_dialog.open = False
        quit_dialog.update()

    def open_quit_dialog():
        page.dialog = quit_dialog
        quit_dialog.open = True
        page.update()   # page.dialogを更新した後にpage.update()が必要

    def quit_app(e):
        overlay_stack.visible = True
        quit_dialog.open = False
        page.update()
        converter.stop_process()
        time.sleep(5)
        page.window_destroy()

    quit_dialog = ft.AlertDialog(
        content=Row(
            alignment=MainAxisAlignment.CENTER,
            controls=[
                Text("終了しますか？（変換処理は中断されます）"),
            ]),
        actions=[
            ft.TextButton("終了する", on_click=quit_app),
            ft.TextButton("キャンセル", on_click=close_quit_dialog),
        ],
        actions_alignment=MainAxisAlignment.END,
    )

    def on_window_close(e):
        if e.data == "close":
            nonlocal is_running_process
            if is_running_process:
                open_quit_dialog()
            else:
                page.window_destroy()

    page.on_window_event = on_window_close
    page.window_prevent_close = True

    overlay_stack = ft.Stack(
        controls=[
            Container(
                width=page.window_width, height=page.window_height,
                alignment=alignment.center,
                bgcolor=colors.with_opacity(0.6, colors.BLACK),
                content=ft.ProgressRing())],
        visible=False)
    page.overlay.append(overlay_stack)

    # set process num (cpu num)

    def set_cpu_num(num):
        cpu_num_slider.current.value = num
        cpu_num_slider.current.update()

    def update_cpu_text(num):
        cpu_num_text.current.value = f"同時プロセス実行数: {num}"
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
                            value=f"同時プロセス実行数: {config.cpu_num_val}",
                            size=16, weight=font_bold),
                        Slider(
                            ref=cpu_num_slider,
                            min=1, max=max_cpu_num,
                            divisions=max_cpu_num-1, width=100,
                            value=config.cpu_num_val,
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
            input_path.current.error_text = "フォルダパスまたはファイルパスを入力してください"
            input_path.current.bgcolor = colors.ON_ERROR
        else:
            input_path.current.error_text = ""
            input_path.current.bgcolor = colors.BACKGROUND

        if is_output_path_empty:
            output_path.current.error_text = "フォルダパスを入力してください"
            output_path.current.bgcolor = colors.ON_ERROR
        else:
            output_path.current.error_text = ""
            output_path.current.bgcolor = colors.BACKGROUND

        if is_input_path_empty or is_output_path_empty:
            page.update()
            return

        # フォルダ名の無効な文字をチェック
        # 全ての文字を検知していないので注意
        invalid_characters = r'[*?"<>|]'
        contain_invalid_char = bool(
            re.search(invalid_characters, output_path.current.value))

        if contain_invalid_char:
            output_path.current.error_text = r'無効な文字 * ? " < > : | が含まれています'
            output_path.current.bgcolor = colors.ON_ERROR
            output_path.current.update()
            return

        input_path_val = input_path.current.value
        output_path_val = output_path.current.value
        file_ext = file_exts_dropdown.current.value.lower()
        if file_ext == exts.PNG_EXT:
            is_lossless = True
        elif file_ext == exts.JPG_EXT:
            is_lossless = False
        else:
            is_lossless = lossless.current.value
        ratio = 100 if is_lossless else int(compression_ratio.current.value)
        is_fill_transparent_val = is_fill_transparent.current.value
        t_color = transparent_color.bgcolor
        cpu_num = cpu_num_slider.current.value

        # save json
        config.save(
            input_path=input_path_val,
            output_path=output_path_val,
            ext=file_ext,
            comp_ratio=ratio,
            is_lossless=is_lossless,
            is_fill_transparent=is_fill_transparent_val,
            transparent_color=t_color,
            cpu_num=cpu_num
        )

        # log
        log_output.current.value = f"入力フォルダパス: {input_path_val}\n"
        log_output.current.value += f"出力フォルダパス: {output_path_val}\n"
        log_output.current.value += f"変換後の拡張子: *.{file_ext}\n"
        log_output.current.value += f"同時プロセス実行数: {cpu_num}\n"
        log_output.current.value += f"可逆圧縮モード: {is_lossless}\n"
        if not is_lossless:
            log_output.current.value += f"品質: {ratio}%\n"
        if is_fill_transparent_val:
            log_output.current.value += f"透過部分の色: {t_color}\n"

        # prevent double clicking
        run_btn.current.disabled = True
        stop_btn.current.disabled = False
        page.add(progress_bar)
        page.update()

        # Actual compression logic goes here
        try:
            nonlocal is_running_process
            is_running_process = True
            os.makedirs(output_path_val, exist_ok=True)
            settings = (input_path_val, output_path_val,
                        file_ext, ratio, is_lossless,
                        is_fill_transparent_val, t_color, cpu_num)

            if converter.can_convert(input_path_val):
                converter.convert_images_in_folder(settings)
                log_output.current.value += "画像の変換が完了しました"
            else:
                log_output.current.value = "画像ファイルが存在しません"

        except ValueError as e:
            log_output.current.value += f"変換中にエラーが発生しました\n{e}"
        finally:
            page.remove(progress_bar)
            run_btn.current.disabled = False
            stop_btn.current.disabled = True
            is_running_process = False
            page.update()

    # stop
    def stop_compression(e):
        converter.stop_process()
        stop_btn.current.disabled = True
        stop_btn.current.update()

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
                                        "AI生成画像のプロンプトを残したまま画像ファイルを圧縮、あるいは拡張子を変換します（アニメーションは非対応）"),
                                    Text(
                                        "ローカル版の画像のプロンプトのみ保存されます。NovelAIのプロンプトやその他のメタデータは保存されません"),
                                    Text("jpg, png, webp, avif 形式に対応しています"),
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
                                        value=config.input_path_val, width=500),
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
                                        value=config.output_path_val, width=500),
                                    ElevatedButton(
                                        content=Icon(icons.FOLDER_OPEN),
                                        width=70, height=45,
                                        on_click=lambda _: pick_output_path_dialog.get_directory_path()),
                                    Container(
                                        width=70, height=45,
                                    ),
                                ]),
                            Row(
                                alignment=MainAxisAlignment.END,
                                controls=[
                                    Container(
                                        alignment=alignment.center_right,
                                        height=25,
                                        content=TextButton(
                                            "入力フォルダを開く", on_click=open_input_dir)),
                                    Container(
                                        alignment=alignment.center_right,
                                        height=25, margin=ft.Margin(0, 0, 30, 0),
                                        content=TextButton(
                                            "出力フォルダを開く", on_click=open_output_dir)),
                                ]),

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
                                                    value=config.ext_val,
                                                    options=[
                                                        dropdown.Option(
                                                            exts.JPG_EXT),
                                                        dropdown.Option(
                                                            exts.PNG_EXT),
                                                        dropdown.Option(
                                                            exts.WEBP_EXT),
                                                        dropdown.Option(
                                                            exts.AVIF_EXT),
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
                                                    value="可逆圧縮モード",
                                                    width=160, size=16,
                                                    weight=font_bold),
                                                Switch(ref=lossless,
                                                       value=config.lossless_val),
                                            ]),
                                        Row(
                                            alignment=MainAxisAlignment.START,
                                            width=260,
                                            controls=[
                                                Text(
                                                    ref=compression_ratio_text,
                                                    value=f"品質: {config.comp_ratio_val} %",
                                                    width=120, size=16,
                                                    weight=font_bold),
                                                Slider(
                                                    ref=compression_ratio,
                                                    label="ファイルサイズ 大",
                                                    min=0, max=100,
                                                    value=config.comp_ratio_val,
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
                                                        value=config.fill_transparent_val,
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
                    height=230,
                    controls=[
                        Container(
                            alignment=alignment.center,
                            padding=20,
                            content=TextField(
                                ref=log_output,
                                label="ログ", value="-", text_size=14,
                                multiline=True, read_only=True, width=600)
                        ),
                    ]),
            ])
    ),

    # 関数で初期化したい場合は、page.add()した後でないと実行できないので注意
    toggle_textfield_border()
    switch_options_value(config.ext_val)
    stop_btn.current.disabled = True
    page.update()


if __name__ == "__main__":
    converter.set_signals()
    ft.app(target=main)
