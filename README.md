# 画像圧縮変換ツール　アッシュくん

## 使用用途

<br>
画像生成AIで作られたプロンプト付き画像を、プロンプトを残したまま拡張子の変更、あるいは画像サイズを圧縮します。<br>

### 詳細

<br><br>
StableDiffusionWebUI (Forge), NovelAI の生成画像に対応しています。<br>
NovelAI 向けに保存する場合は "<b>png, webp</b>"形式のいずれかで保存してください。
<br><br>
ComfyUI の生成画像を jpg, webp, avif 形式に変換すると、メタデータは画像に保持されますが、ComfyUI でプロンプトやワークフローを読み込むことはできません。<br>
再び ComfyUI でプロンプトを読み込みたい場合は、本ツールで png 形式に再度変換することで、読み込めるようになります。
<br><br>
画像は"<b>png, jpg, webp, avif</b>" 形式に変換できます。
<br><br>
アニメーション画像や上記のファイル形式以外のファイルは非対応です。
<br><br><br>

## 推奨環境

Windows10, 11<br>
Python3.8 以上
<br><br><br>

## 導入方法

#### 方法 ①（かんたん）：<br><br>

"<b>run.bat</b>" を実行してください。<br>
自動で仮想環境を作成してモジュールをインストールした後、アプリを起動します。<br>
（"Windows によって PC が保護されました" と表示された場合、"詳細" から "実行" をクリックしてください）
<br><br>

#### 方法 ②（Python わかる人向け）：<br><br>

コマンドプロンプトから以下のコードを実行してください。<br>

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

<br><br><br>

## 起動方法

#### 方法 ①：<br>

"<b>run.bat</b>" を実行するとアプリが起動します。
<br><br>

#### 方法 ②：<br>

```
venv\Scripts\activate
python main.py
```

仮想環境を立ち上げてから上記のスクリプトを実行してください。
<br><br><br>

## 使い方

<img width="400" alt="screenshot" src="https://github.com/takep6/image-converter-with-prompts/assets/74190436/df886dcd-391d-4f8f-8515-66f0d0860100">
<br><br>

画像の入ったフォルダ（入力フォルダパス）と出力先（出力フォルダパス）を選択してください。<br>
出力後のフォーマットは（jpg, png, webp, avif）から選べます。<br>
実行ボタンを押すと変換を開始し、停止ボタンを押すと途中で終了します。
<br><br><br>

## 設定項目

#### 入力フォルダパス：

変換したい画像のファイルパス、またはフォルダパスを指定します。
<br><br>

#### 出力フォルダパス：

変換後の画像を保存するフォルダパスを指定します。<br>
フォルダが存在しない場合は新しく作成されます。
<br><br>

#### サブフォルダを対象にする：

入力フォルダパスにフォルダを指定した場合、そのフォルダ内の全てのサブフォルダに対して変換処理を行うかどうかを設定します。
<br><br>

#### 変換後の拡張子：

出力する画像の画像形式を決定します。<br>
png, jpg, webp, avif から選択できます。
<br><br>

#### 可逆圧縮モード：

画質を劣化させずに圧縮（lossless）するかどうかを選択します。<br>
"変換後の拡張子" を変更すると、以下のように自動で切り替わります。<br>
jpg -> OFF <br>
png -> ON <br>
webp -> ON/OFF 選択可能 <br>
avif -> OFF
<br><br>

#### 品質：

画像の圧縮率を決めます。値が高いほど元の画像に近い画質になりますが、ファイルサイズが大きくなります。<br>
可逆圧縮モードが "OFF" の場合のみ適用されます。
<br><br>

#### 透過部分を塗りつぶす：

透明な部分がある画像（主に png, webp, avif）の透過部分を一色で塗りつぶすかどうか決めます。
<br><br>

#### 透明部分の色：

透明な部分を選択した色で一色に塗りつぶします。<br>
"透過部分を塗りつぶす" が "ON" の場合のみ適用されます。
<br><br>

#### 実行ボタン：

変換処理を実行します。
<br><br>

#### 停止ボタン：

変換処理を途中で終了します。
<br><br>

#### 設定アイコンボタン：

サイドメニューを開きます。
<br><br>

#### 同時プロセス実行数：

画像変換処理を同時に実行する最大数を決めます。<br>
画像の枚数が多い場合、値を大きくした方が処理時間を短縮できます。
<br><br>

#### テーマ：

ライトテーマ/ダークテーマを切り替えます。
<br><br><br>

## ライセンス

このプロジェクトは [AGPL-3.0 license](LICENSE.txt) ライセンスの元にライセンスされています。
<br><br><br>

## 謝辞

[stable-diffusion-webui（AUTOMATIC1111 氏）](https://github.com/AUTOMATIC1111/stable-diffusion-webui)<br>
[stable-diffusion-webui-forge（lllyasviel 氏）](https://github.com/lllyasviel/stable-diffusion-webui-forge)
<br><br>
アプリを製作するにあたって上記プロジェクトより一部のコードを使用させていただきました。深く感謝いたします。
