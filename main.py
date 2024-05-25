import os
import re
import time

import flet
import psutil
from flet import (AlertDialog, Card, Checkbox, Column, Container,
                  CrossAxisAlignment, Divider, Dropdown, ElevatedButton,
                  FilePicker, FilePickerFileType, FilePickerResultEvent,
                  FloatingActionButton, FontWeight, Icon, MainAxisAlignment,
                  Margin, NavigationDrawer, ProgressBar, ProgressRing, Ref,
                  Row, ScrollMode, Slider, Stack, Switch, Text, TextButton,
                  TextDecoration, TextField, TextSpan, TextStyle, alignment,
                  colors, dropdown, icons)
from flet_contrib.color_picker import ColorPicker

import image_converter.exts as exts
import image_converter.image_converter as converter
from image_converter.config_loader import ConfigLoader
from image_converter.theme_loader import ThemeLoader


def main(page):
    # variables
    font_bold = FontWeight.BOLD
    is_running_process = False
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    config = ConfigLoader()
    theme = ThemeLoader()

    # page settings
    page.title = "Image Converter with prompts"
    page.theme_mode = theme.theme
    page.horizontal_alignment = CrossAxisAlignment.CENTER
    page.padding = 30
    page.window_width = 800
    page.window_height = 1000
    max_cpu_num = psutil.cpu_count(logical=True)

    # Control Ref
    input_path_textfield = Ref[TextField]()
    output_path_textfield = Ref[TextField]()
    file_exts_dropdown = Ref[Dropdown]()
    quality_slider = Ref[Slider]()
    quality_text = Ref[Text]()
    lossless = Ref[Switch]()
    log_output = Ref[TextField]()
    run_btn = Ref[ElevatedButton]()
    stop_btn = Ref[ElevatedButton]()
    fill_color_checkbox = Ref[Checkbox]()
    cpu_num_slider = Ref[Slider]()
    cpu_num_text = Ref[Text]()
    is_convert_all_subfolders = Ref[Checkbox]()

    # ColorPicker
    def open_color_picker(e):
        page.dialog = color_dialog
        color_dialog.open = True
        page.update()

    color_picker = ColorPicker(color=config.fill_color, width=300)
    fill_color = Container(
        width=60, height=35, border_radius=5,
        bgcolor=config.fill_color,
        on_click=open_color_picker)

    def change_color(e):
        fill_color.bgcolor = color_picker.color
        color_dialog.open = False
        page.update()

    def close_dialog(e):
        color_dialog.open = False
        color_dialog.update()

    color_dialog = AlertDialog(
        content=color_picker,
        actions=[
            TextButton("決定", on_click=change_color),
            TextButton("キャンセル", on_click=close_dialog),
        ],
        actions_alignment=MainAxisAlignment.END,
    )

    # FilePicker

    def select_input_path(e: FilePickerResultEvent):
        input_path_textfield.current.value = e.path if e.path \
            else input_path_textfield.current.value
        if input_path_textfield.current.value != "":
            input_path_textfield.current.bgcolor = colors.BACKGROUND
            input_path_textfield.current.error_text = ""
        input_path_textfield.current.update()

    def select_output_path(e: FilePickerResultEvent):
        output_path_textfield.current.value = e.path if e.path \
            else output_path_textfield.current.value
        if output_path_textfield.current.value != "":
            output_path_textfield.current.bgcolor = colors.BACKGROUND
            output_path_textfield.current.error_text = ""
        output_path_textfield.current.update()

    def select_input_filepath(e: FilePickerResultEvent):
        input_path_textfield.current.value = e.files[0].path \
            if e.files else input_path_textfield.current.value
        if input_path_textfield.current.value != "":
            input_path_textfield.current.bgcolor = colors.BACKGROUND
            input_path_textfield.current.error_text = ""
        input_path_textfield.current.update()

    pick_input_path_dialog = FilePicker(on_result=select_input_path)
    pick_output_path_dialog = FilePicker(on_result=select_output_path)
    pick_input_filepath_dialog = FilePicker(on_result=select_input_filepath)
    page.overlay.extend([
        pick_input_path_dialog,
        pick_output_path_dialog,
        pick_input_filepath_dialog
    ])

    # compression value
    def change_quality_label(ratio):
        if ratio <= 30:
            quality_slider.current.label = "ファイルサイズ 小"
        elif ratio <= 70:
            quality_slider.current.label = "ファイルサイズ 中"
        else:
            quality_slider.current.label = "ファイルサイズ 大"

    def set_quality_to_text(ratio):
        quality_text.current.value = f"品質: {ratio} %"
        quality_text.current.update()

    def set_quality(ratio):
        quality_slider.current.value = ratio

    def change_quality(e):
        ratio = int(e.control.value)
        set_quality(ratio)
        change_quality_label(ratio)
        set_quality_to_text(ratio)
        quality_slider.current.update()

    # progress bar
    conversion_pb = ProgressBar(width=600, color=colors.BLUE, value=0)
    pb_text = Text("")
    progress_bar_row = Row(
        alignment=MainAxisAlignment.CENTER,
        controls=[
            conversion_pb,
            pb_text,
        ]
    )

    def init_progress_bar():
        page.add(progress_bar_row)
        conversion_pb.color = colors.AMBER_400
        conversion_pb.value = None
        pb_text.value = ""
        page.update()

    def start_progress_bar(current, total):
        conversion_pb.value = 0
        conversion_pb.color = colors.BLUE
        pb_text.value = f"{current}/{total}"
        page.update()

    def update_progress_bar(current, total):
        conversion_pb.value = current / total
        pb_text.value = f"{current}/{total}"
        conversion_pb.update()
        pb_text.update()

    def complete_progress_bar():
        conversion_pb.color = colors.GREEN
        conversion_pb.update()

    def error_progress_bar():
        conversion_pb.color = colors.ERROR
        conversion_pb.update()

    # format value

    def switch_options_value(ext):
        if ext == exts.PNG_EXT:
            lossless.current.value = True
            lossless.current.disabled = True
            set_quality(100)
            set_quality_to_text(100)
            quality_slider.current.disabled = True
            fill_color_checkbox.current.disabled = False
        elif ext == exts.JPG_EXT:
            lossless.current.value = False
            lossless.current.disabled = True
            quality_slider.current.disabled = False
            fill_color_checkbox.current.value = True
            fill_color_checkbox.current.disabled = True
        elif ext == exts.AVIF_EXT:
            lossless.current.value = False
            lossless.current.disabled = True
            quality_slider.current.disabled = False
            fill_color_checkbox.current.disabled = False
        else:
            lossless.current.disabled = False
            quality_slider.current.disabled = False
            fill_color_checkbox.current.disabled = False

    def select_ext(e):
        switch_options_value(e.control.value)
        page.update()

    def open_input_dir(e):
        # ファイルかフォルダかを判別
        path = input_path_textfield.current.value
        path = os.path.dirname(path) if os.path.isfile(path) else path
        open_dir(path)

    def open_output_dir(e):
        open_dir(output_path_textfield.current.value)

    def open_dir(path):
        # OS によって適切なコマンドを使ってフォルダを開く
        if os.name == 'nt':  # Windows の場合
            os.system(f'explorer "{path}"')
        elif os.name == 'posix':  # macOS や Linux の場合
            os.system(f'open "{path}"')
        else:
            print("この OS はサポートされていません。")

    # toggle theme
    def get_textfield_border_color():
        return colors.BLACK if page.theme_mode == LIGHT_THEME \
            else colors.BLUE_600

    def toggle_textfield_border():
        border_color = get_textfield_border_color()
        input_path_textfield.current.border_color = border_color
        output_path_textfield.current.border_color = border_color
        log_output.current.border_color = border_color

    def toggle_theme(e):
        page.theme_mode = LIGHT_THEME if page.theme_mode == DARK_THEME \
            else DARK_THEME
        toggle_textfield_border()
        theme.save(page.theme_mode)
        page.update()

    def toggle_transparency(e):
        fill_color_checkbox.current.value = e.control.value
        fill_color_checkbox.current.update()

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

    quit_dialog = AlertDialog(
        content=Row(
            alignment=MainAxisAlignment.CENTER,
            controls=[
                Text("終了しますか？（変換処理は中断されます）"),
            ]),
        actions=[
            TextButton("終了する", on_click=quit_app),
            TextButton("キャンセル", on_click=close_quit_dialog),
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

    overlay_stack = Stack(
        controls=[
            Container(
                width=page.window_width, height=page.window_height,
                alignment=alignment.center,
                bgcolor=colors.with_opacity(0.6, colors.BLACK),
                content=ProgressRing())],
        visible=False)
    page.overlay.append(overlay_stack)

    # set process num (cpu num)
    def change_cpu_num(e):
        cpu_num = int(e.control.value)
        cpu_num_slider.current.value = cpu_num
        cpu_num_text.current.value = f"同時プロセス実行数: {cpu_num}"
        cpu_num_slider.current.update()
        cpu_num_text.current.update()

    def toggle_subfolders_check(e):
        is_convert_all_subfolders.current.value = e.data
        is_convert_all_subfolders.current.update()

    # detailed configuration
    end_drawer = NavigationDrawer(
        controls=[
            Container(
                padding=30, alignment=alignment.center,
                content=Row(
                    alignment=MainAxisAlignment.CENTER,
                    controls=[
                        Icon(icons.SETTINGS),
                        Text(value="詳細設定", size=24, weight=font_bold),
                    ])),
            Divider(),
            Container(
                padding=20, alignment=alignment.center,
                content=Row(
                    alignment=MainAxisAlignment.CENTER,
                    controls=[
                        Text(
                            ref=cpu_num_text,
                            value=f"同時プロセス実行数: {config.cpu_num}",
                            size=16, weight=font_bold),
                        Slider(
                            ref=cpu_num_slider,
                            min=1, max=max_cpu_num,
                            divisions=max_cpu_num-1, width=100,
                            value=config.cpu_num,
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

    page.floating_action_button = FloatingActionButton(
        icon=icons.SETTINGS, on_click=show_end_drawer)

    # run
    def run_conversion(e):
        # check input value
        is_input_path_empty = input_path_textfield.current.value == ""
        is_output_path_empty = output_path_textfield.current.value == ""

        if is_input_path_empty:
            input_path_textfield.current.error_text = "フォルダパスまたはファイルパスを入力してください"
            input_path_textfield.current.bgcolor = colors.ON_ERROR
        else:
            input_path_textfield.current.error_text = ""
            input_path_textfield.current.bgcolor = colors.BACKGROUND

        if is_output_path_empty:
            output_path_textfield.current.error_text = "フォルダパスを入力してください"
            output_path_textfield.current.bgcolor = colors.ON_ERROR
        else:
            output_path_textfield.current.error_text = ""
            output_path_textfield.current.bgcolor = colors.BACKGROUND

        if is_input_path_empty or is_output_path_empty:
            input_path_textfield.current.update()
            output_path_textfield.current.update()
            return

        # フォルダ名の無効な文字をチェック
        # 全ての文字を検知していないので注意
        invalid_characters = r'[*?"<>|]'
        contain_invalid_char = bool(
            re.search(invalid_characters, output_path_textfield.current.value))

        if contain_invalid_char:
            output_path_textfield.current.error_text = r'無効な文字 * ? " < > : | が含まれています'
            output_path_textfield.current.bgcolor = colors.ON_ERROR
            output_path_textfield.current.update()
            return

        input_path = input_path_textfield.current.value
        output_path = output_path_textfield.current.value
        is_convert_subfolders = is_convert_all_subfolders.current.value
        file_ext = file_exts_dropdown.current.value.lower()
        if file_ext == exts.PNG_EXT:
            is_lossless = True
        elif file_ext == exts.JPG_EXT:
            is_lossless = False
        else:
            is_lossless = lossless.current.value
        quality = 100 if is_lossless else int(quality_slider.current.value)
        is_fill_color = fill_color_checkbox.current.value
        t_color = fill_color.bgcolor
        cpu_num = cpu_num_slider.current.value

        # save json
        config.save(
            input_path=input_path,
            output_path=output_path,
            is_convert_subfolders=is_convert_subfolders,
            ext=file_ext,
            quality=quality,
            is_lossless=is_lossless,
            is_fill_color=is_fill_color,
            fill_color=t_color,
            cpu_num=cpu_num
        )

        # log
        log_output.current.value = f"入力フォルダパス: {input_path}\n"
        log_output.current.value += f"出力フォルダパス: {output_path}\n"
        log_output.current.value += f"変換後の拡張子: *.{file_ext}\n"
        log_output.current.value += f"同時プロセス実行数: {cpu_num}\n"
        lossless_msg = "ON" if is_lossless else "OFF"
        log_output.current.value += f"可逆圧縮モード: {lossless_msg}\n"
        if not is_lossless:
            log_output.current.value += f"品質: {quality}%\n"
        if is_fill_color:
            log_output.current.value += f"透過部分の色: {t_color}\n"

        # prevent double clicking
        run_btn.current.disabled = True
        stop_btn.current.disabled = False
        log_output.current.error_text = ""
        log_output.current.bgcolor = colors.BACKGROUND
        init_progress_bar()
        page.update()

        # Actual comversion logic goes here
        nonlocal is_running_process
        is_running_process = True

        start_time = time.time()
        # 実行
        isError, message = converter.convert_images_concurrently(
            input_path=input_path,
            output_path=output_path,
            is_convert_subfolders=is_convert_subfolders,
            output_format=file_ext,
            quality=quality,
            is_lossless=is_lossless,
            is_fill_color=is_fill_color,
            fill_color=t_color,
            cpu_num=cpu_num,
            pb_callbacks={"start": start_progress_bar,
                          "update": update_progress_bar,
                          "complete": complete_progress_bar,
                          "error": error_progress_bar}
        )

        log_output.current.value += message

        end_time = time.time()

        if isError:
            log_output.current.error_text = "---"
            log_output.current.bgcolor = colors.ON_ERROR
        else:
            log_output.current.error_text = ""
            log_output.current.bgcolor = colors.BACKGROUND
            log_output.current.value += f"\n処理時間: {round(end_time - start_time, 3)} sec."

        run_btn.current.disabled = False
        stop_btn.current.disabled = True
        is_running_process = False
        page.update()

    # stop
    def stop_conversion(e):
        converter.stop_process()
        stop_btn.current.disabled = True
        stop_btn.current.update()

    def highlight_link(e):
        e.control.style.color = colors.BLUE
        e.control.update()

    def unhighlight_link(e):
        e.control.style.color = None
        e.control.update()

    desc01 = "AI生成画像のプロンプトを残したまま、画像ファイルの圧縮や拡張子の変換を行います。（アニメーションは非対応）"
    desc02 = "主にStableDiffusionWebUI(Forge)の画像向けです。ComfyUIやNovelAIも一応対応しています。"
    desc03 = "jpg, png, webp, avif 形式に対応しています。　詳しい使い方や注意点は "
    desc04 = "こちら"

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
                                    Text(desc01),
                                    Text(desc02),
                                    Text(desc03, spans=[
                                        TextSpan(
                                            desc04,
                                            TextStyle(
                                                decoration=TextDecoration.UNDERLINE),
                                            url=r"https://github.com/takep6/image-converter-with-prompts#%E4%BD%BF%E3%81%84%E6%96%B9",
                                            on_enter=highlight_link,
                                            on_exit=unhighlight_link)]),
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
                                        ref=input_path_textfield,
                                        label="入力フォルダパス",
                                        value=config.input_path, width=500),
                                    ElevatedButton(
                                        content=Icon(icons.FOLDER_OPEN),
                                        width=70, height=45,
                                        on_click=lambda _: pick_input_path_dialog.get_directory_path()),
                                    ElevatedButton(
                                        content=Icon(icons.IMAGE),
                                        width=70, height=45,
                                        on_click=lambda _: pick_input_filepath_dialog.pick_files(
                                            allow_multiple=True,
                                            file_type=FilePickerFileType.IMAGE,
                                            allowed_extensions=[
                                                "jpeg", "jpg", "png", "webp", "avif"],
                                        )),
                                ]),
                            Row(
                                alignment=MainAxisAlignment.CENTER,
                                controls=[
                                    TextField(
                                        ref=output_path_textfield,
                                        label="出力フォルダパス",
                                        value=config.output_path, width=500),
                                    ElevatedButton(
                                        content=Icon(icons.FOLDER_OPEN),
                                        width=70, height=45,
                                        on_click=lambda _: pick_output_path_dialog.get_directory_path()),
                                    Container(
                                        width=70, height=45,
                                    ),
                                ]),
                            Row(
                                alignment=MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    Container(
                                        width=250,
                                        height=25,
                                        content=Row(
                                            alignment=MainAxisAlignment.CENTER,
                                            controls=[
                                                Checkbox(
                                                    ref=is_convert_all_subfolders,
                                                    value=config.is_convert_subfolders,
                                                    on_change=toggle_subfolders_check
                                                ),
                                                Text(
                                                    "サブフォルダを対象にする", weight=font_bold),
                                            ]),
                                    ),
                                    Container(
                                        width=400,
                                        height=25,
                                        content=Row(
                                            alignment=MainAxisAlignment.END,
                                            controls=[
                                                Container(
                                                    alignment=alignment.center_right,
                                                    height=25,
                                                    content=TextButton(
                                                        "入力フォルダを開く", on_click=open_input_dir)),
                                                Container(
                                                    alignment=alignment.center_right,
                                                    height=25, margin=Margin(0, 0, 30, 0),
                                                    content=TextButton(
                                                        "出力フォルダを開く", on_click=open_output_dir)),
                                            ]),
                                    ),
                                ]
                            ),

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
                                                    value=config.ext,
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
                                                       value=config.lossless),
                                            ]),
                                        Row(
                                            alignment=MainAxisAlignment.START,
                                            width=260,
                                            controls=[
                                                Text(
                                                    ref=quality_text,
                                                    value=f"品質: {config.quality} %",
                                                    width=120, size=16,
                                                    weight=font_bold),
                                                Slider(
                                                    ref=quality_slider,
                                                    label="ファイルサイズ 大",
                                                    min=0, max=100,
                                                    value=config.quality,
                                                    width=140, divisions=20,
                                                    on_change=change_quality),
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
                                                        ref=fill_color_checkbox,
                                                        value=config.is_fill_color,
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
                                                    fill_color,
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
                                                on_click=run_conversion),
                                            ElevatedButton(
                                                ref=stop_btn,
                                                icon=icons.STOP, text="停止",
                                                width=110, height=60,
                                                on_click=stop_conversion,
                                                disabled=True)
                                        ]),
                                )
                            ]),
                    ]),
                Column(
                    scroll=ScrollMode.ALWAYS,
                    height=230,
                    controls=[
                        Container(
                            alignment=alignment.center,
                            padding=20,
                            content=TextField(
                                ref=log_output,
                                label="ログ", value="-", text_size=14,
                                multiline=True, read_only=True, width=700, filled=False)
                        ),
                    ]),
            ])
    ),

    # page.add()した後に実行する
    toggle_textfield_border()
    switch_options_value(config.ext)
    page.update()


if __name__ == "__main__":
    converter.set_signals()
    flet.app(target=main)
