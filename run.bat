@echo off

REM バッチファイルの存在するフォルダのパスを取得
set "SCRIPT_DIR=%~dp0"

REM 仮想環境のパスを設定
set "VENV_DIR=%SCRIPT_DIR%venv"

REM 仮想環境の有無を確認
if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
)

REM 仮想環境をアクティベート
call "%VENV_DIR%\Scripts\activate.bat"

REM requirements.txtからモジュールリストを取得
pip freeze > installed_modules.txt

REM インストールされていないモジュールをチェック
for /f %%m in (requirements.txt) do (
    findstr /c:"%%m" installed_modules.txt > nul || (
        pip install %%m
    )
)

REM 一時ファイルを削除
del installed_modules.txt

REM main.pyを実行
python main.py
