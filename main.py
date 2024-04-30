import json
import os

import flet as ft
from flet import (Card, Column, Container, Dropdown, ElevatedButton,
                  FilePicker, FilePickerResultEvent, Icon, MainAxisAlignment,
                  ProgressBar, Row, Slider, Switch, Text, TextButton,
                  TextField, alignment, colors, dropdown, icons)

import convert_to_webp as cv_webp

"""
TODO:
入力フォルダに画像が存在しなかった場合のエラーチェック
透明背景の画像は変換できるかチェック
dpi、ビット数など画像データが問題なく変換できているかチェック
巨大な画像が変換できるか、大量の画像でも問題なく完遂できるかチェック
コードのリファクタリング
"""


def main(page):
    # page settings
    page.title = "Image Ext Converter"
    page.padding = 30
    page.window_width = 800
    page.window_height = 1000

    # json keys
    input_key = "input_path"
    output_key = "output_path"
    ext_key = "ext_path"
    comp_ratio_key = "comp_ratio"
    lossless_key = "lossless"

    # json filename
    datafile = "data.json"

    # create data
    if not os.path.exists(datafile):
        with open(datafile, "w") as f:
            new_data = {
                input_key: "",
                output_key: "",
                ext_key: "webp",
                comp_ratio_key: 100,
                lossless_key: False
            }
            json.dump(new_data, f, indent=4)

    # set init values
    try:
        with open(datafile, "r")as f:
            data = json.load(f)
            init_input_path = data[input_key]
            init_output_path = data[output_key]
            init_ext = data[ext_key]
            init_compression_ratio = data[comp_ratio_key]
            init_lossless = data[lossless_key]
    except Exception as e:
        print(e, "jsonデータのロードに失敗しました。初期値でアプリを開始します。")
        init_input_path = ""
        init_output_path = ""
        init_ext = "webp"
        init_compression_ratio = 100
        init_lossless = False

    font_bold = ft.FontWeight.BOLD

    # descriptions
    description01 = Text(
        "AI生成画像のプロンプトを残したまま画像ファイルの拡張子を変換します")
    description02 = Text("入力・出力ファイル形式はjpg, png, webpのみ対応")

    # Input path field
    input_path = TextField(label="入力フォルダパス",
                           value=init_input_path,
                           width=500)

    # Output path field
    output_path = TextField(label="出力フォルダパス",
                            value=init_output_path,
                            width=500)

    # File/folder selection buttons
    def select_input_path(e: FilePickerResultEvent):
        input_path.value = e.path if e.path else ""
        if input_path.value != "":
            input_path.bgcolor = colors.WHITE
            input_path.error_text = ""
            page.client_storage.set(input_key, input_path.value)
        input_path.update()

    def select_output_path(e: FilePickerResultEvent):
        output_path.value = e.path if e.path else ""
        if output_path.value != "":
            output_path.bgcolor = colors.WHITE
            output_path.error_text = ""
            page.client_storage.set(output_key, output_path.value)
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

    def select_ext(e):
        switch_settings(e.control.value)

    # Dropdown for file types
    file_types = Dropdown(
        value=init_ext,
        options=[
            dropdown.Option("jpg"),
            dropdown.Option("png"),
            dropdown.Option("webp"),
        ],
        label="Format",
        width=80,
        on_change=select_ext
    )

    def set_comp_ratio_val(e):
        comp_val = int(e.control.value)
        comp_ratio_val_text.value = f"圧縮率: {str(comp_val)}  %"
        if comp_val <= 30:
            compression_ratio.label = "ファイルサイズ 小"
        elif comp_val <= 70:
            compression_ratio.label = "ファイルサイズ 中"
        else:
            compression_ratio.label = "ファイルサイズ 大"
        page.update()

    # Compression ratio input
    compression_ratio = Slider(
        min=0, max=100,
        label="ファイルサイズ 大",
        value=init_compression_ratio, width=150, divisions=20,
        on_change=set_comp_ratio_val)
    comp_ratio_val_text = Text(
        value=f"圧縮率: {init_compression_ratio} %", width=120, weight=font_bold, color=colors.BLACK87, size=16)

    # Checkboxes for compression types
    lossless = Switch(value=init_lossless)

    # Log output
    log_output = TextField(
        label="ログ", value="-", multiline=True, read_only=True, width=600, )

    progress_bar = ProgressBar(width=600, color=colors.AMBER_400)

    def switch_settings(ext):
        if ext == "png":
            lossless.disabled = True
            compression_ratio.disabled = True
        elif ext == "jpg":
            lossless.disabled = True
            compression_ratio.disabled = False
        else:
            lossless.disabled = False
            compression_ratio.disabled = False
        page.update()

    switch_settings(init_ext)

    def open_output_dir(e):
        # OS によって適切なコマンドを使ってフォルダを開く
        if os.name == 'nt':  # Windows の場合
            os.system(f'explorer "{output_path.value}"')
        elif os.name == 'posix':  # macOS や Linux の場合
            os.system(f'open "{output_path.value}"')
        else:
            print("この OS はサポートされていません。")

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
        if file_ext == "png":
            is_lossless = True
        elif file_ext == "jpg":
            is_lossless = False
        else:
            is_lossless = lossless.value
        ratio = 100 if is_lossless else int(compression_ratio.value)

        # save json
        with open(datafile, "w") as f:
            update_data = {
                input_key: input_dir,
                output_key: output_dir,
                ext_key: file_ext,
                comp_ratio_key: ratio,
                lossless_key: is_lossless
            }
            json.dump(update_data, f, indent=4)

        # log
        log_output.value = ""
        log_output.value = f"Input Path: {input_dir}\n"
        log_output.value += f"Output Path: {output_dir}\n"
        log_output.value += f"Format: *.{file_ext}\n"
        if is_lossless:
            log_output.value += f"Lossless: {is_lossless}\n"
        else:
            log_output.value += f"Compression Ratio: {ratio}%\n"
        run_btn.disabled = True
        page.add(progress_bar)
        page.update()

        # Actual compression logic goes here
        try:
            cv_webp.convert_images_in_folder(
                folder_path=input_dir,
                output_path=output_dir,
                output_format=file_ext,
                quality=ratio,
                lossless=is_lossless
            )
            log_output.value += "Completed!"
        except Exception as e:
            log_output.value += "変換中にエラーが発生しました"
            log_output.value += str(e)
        finally:
            page.remove(progress_bar)
            run_btn.disabled = False
            page.update()

    run_btn = ElevatedButton(
        text="実行", on_click=run_compression, width=180, height=150)

    page.add(
        Column(
            width=800,
            controls=[
                Container(Text("画像圧縮変換ツール　アッシュ君", size=40, weight=font_bold),
                          alignment=alignment.center, padding=20),
                Container(Card(
                    Container(
                        Column([
                            description01,
                            description02
                        ]), padding=20),
                    margin=10), alignment=alignment.center),
                Container(
                    Column([
                        Row([
                            input_path,
                            input_file_btn],
                            alignment=MainAxisAlignment.CENTER),
                        Row([output_path, output_file_btn],
                            alignment=MainAxisAlignment.CENTER),
                    ]), padding=20),
                Container(TextButton(
                    "出力フォルダを開く", on_click=open_output_dir), height=20, margin=ft.Margin(0, 0, 50, 0), alignment=alignment.center_right),
                Row([
                    Card(
                        Container(
                            Column([
                                Row([
                                    Text(value="変換後の拡張子", width=150,
                                         weight=font_bold, color=colors.BLACK87, size=16),
                                    file_types,
                                ], width=250, alignment=MainAxisAlignment.START),
                                Row([
                                    Text(value="可逆圧縮", width=160,
                                         weight=font_bold, color=colors.BLACK87, size=16),
                                    lossless
                                ], width=250, alignment=MainAxisAlignment.START),
                                Row([
                                    comp_ratio_val_text,
                                    compression_ratio,
                                ], width=250, alignment=MainAxisAlignment.START),
                            ], height=200, alignment=MainAxisAlignment.SPACE_BETWEEN), padding=20, width=300)),
                    Container(
                        Column([
                            run_btn
                        ]), padding=20),
                ], alignment=MainAxisAlignment.SPACE_EVENLY),
                Column([Container(log_output, padding=20,
                       alignment=alignment.center)], height=200, scroll=ft.ScrollMode.ALWAYS),
            ])
    ),


ft.app(target=main)
