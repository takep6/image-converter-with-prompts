import os

import flet as ft
from flet import (Card, Column, Container, CrossAxisAlignment, Dropdown,
                  ElevatedButton, FilePicker, FilePickerResultEvent, Icon,
                  MainAxisAlignment, Row, Slider, Switch, Text, TextField,
                  alignment, colors, dropdown, icons)

import convert_to_webp as cv_webp

"""
TODO: jpgだけ非可逆圧縮ができず、エラーが発生してしまう。要修正
"""


def main(page):
    # ページ設定
    page.title = "Image Ext Converter"
    page.vertical_alignment = MainAxisAlignment.CENTER
    page.horizontal_alignment = CrossAxisAlignment.CENTER
    page.padding = 30
    page.window_width = 700
    page.window_height = 800

    description01 = Text(value="AI生成画像のプロンプトを保持したまま画像ファイルの拡張子を変換します")
    description02 = Text("拡張子はjpg, png, webpのみ対応")

    # Input path field
    input_path = TextField(label="Input Folder Path",
                           width=500)

    # Output path field
    output_path = TextField(label="Output Folder Path", width=500)

    # File/folder selection buttons
    def select_input_path(e: FilePickerResultEvent):
        input_path.value = e.path if e.path else ""
        if input_path.value != "":
            input_path.bgcolor = colors.WHITE
            input_path.error_text = ""
        input_path.update()

    def select_output_path(e: FilePickerResultEvent):
        output_path.value = e.path if e.path else ""
        if output_path.value != "":
            output_path.bgcolor = colors.WHITE
            output_path.error_text = ""
        output_path.update()

    pick_input_path_dialog = FilePicker(on_result=select_input_path)
    pick_output_path_dialog = FilePicker(on_result=select_output_path)
    page.overlay.extend([pick_input_path_dialog, pick_output_path_dialog])

    input_file_btn = ElevatedButton(
        content=Icon(icons.FOLDER_OPEN,),
        width=80, height=60,
        on_click=lambda _: pick_input_path_dialog.get_directory_path())
    output_file_btn = ElevatedButton(
        content=Icon(icons.FOLDER_OPEN),
        width=80, height=60,
        on_click=lambda _: pick_output_path_dialog.get_directory_path())

    # Dropdown for file types
    file_types = Dropdown(
        value="webp",
        options=[
            dropdown.Option("jpg"),
            dropdown.Option("png"),
            dropdown.Option("webp"),
        ],
        label="Format",
        width=80,
    )

    def set_comp_ratio_val(e):
        comp_ratio_val_text.value = f"圧縮率: {str(int(e.control.value))}  %"
        page.update()

    # Compression ratio input
    compression_ratio = Slider(
        min=0, max=100,
        label="Compression Ratio",
        value=100, width=150, divisions=20,
        on_change=set_comp_ratio_val)
    comp_ratio_val_text = Text(
        value=f"圧縮率: {int(compression_ratio.value)} %", width=100)

    def toggle_lossless(e):
        compression_ratio.disabled = e.control.value
        page.update()

    # Checkboxes for compression types
    lossless = Switch(value=False, on_change=toggle_lossless)

    # Log output
    log_output = TextField(
        label="Log", multiline=True, read_only=True, width=600)

    def run_compression(e):
        is_not_exist_path = input_path.value == "" or output_path.value == ""
        if input_path.value == "":
            input_path.error_text = "Input Pathにフォルダパスを入力してください"
            input_path.bgcolor = ft.colors.RED_100
        if output_path.value == "":
            output_path.error_text = "Output Pathにフォルダパスを入力してください"
            output_path.bgcolor = ft.colors.RED_100
        if is_not_exist_path:
            page.update()
            return

        input_dir = input_path.value
        output_dir = output_path.value
        file_ext = file_types.value.lower()
        is_lossless = lossless.value
        ratio = 100 if is_lossless else compression_ratio.value

        log_output.value = ""
        log_output.value = f"Input Path: {input_dir}\n"
        log_output.value += f"Output Path: {output_dir}\n"
        log_output.value += f"Format: *.{file_ext}\n"
        if is_lossless:
            log_output.value += f"Lossless: {is_lossless}\n"
        else:
            log_output.value += f"Compression Ratio: {ratio}%\n"
        page.update()

        # Actual compression logic goes here
        cv_webp.convert_images_in_folder(
            folder_path=input_dir,
            output_path=output_dir,
            output_format=file_ext,
            quality=ratio,
            lossless=is_lossless
        )

        log_output.value += "Completed!"
        page.update()

    run_btn = ElevatedButton(
        text="Run", on_click=run_compression, width=180, height=150)

    page.add(
        Column(
            width=800,
            controls=[
                Container(Card(
                    Container(
                        Column([
                            description01,
                            description02,
                        ]), padding=20),
                    margin=10), alignment=alignment.center),
                Container(
                    Column([
                        Row([input_path, input_file_btn],
                            alignment=MainAxisAlignment.CENTER),
                        Row([output_path, output_file_btn],
                            alignment=MainAxisAlignment.CENTER),
                    ]), padding=20),
                Row([
                    Container(
                        Column([
                            Row([
                                Text("変換後の拡張子"),
                                file_types,
                            ]),
                            Row([
                                Text(value="可逆圧縮"),
                                lossless
                            ]),
                            Row([
                                comp_ratio_val_text,
                                compression_ratio,
                            ]),
                        ]), padding=20),
                    Container(run_btn, padding=20, alignment=alignment.center),
                ], alignment=MainAxisAlignment.CENTER),
                Container(log_output, padding=20, alignment=alignment.center),
            ])
    ),


ft.app(target=main)
