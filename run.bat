@echo off
REM バッチファイルのディレクトリを取得
set SCRIPT_DIR=%~dp0

REM 仮想環境を有効化
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

REM requirements.txtの内容に基づいて必要なパッケージをインストール
pip install -r "%SCRIPT_DIR%requirements.txt"

REM main.py スクリプトを実行
python "%SCRIPT_DIR%main.py"
