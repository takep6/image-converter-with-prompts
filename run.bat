@echo off

rem 仮想環境の有効化
call venv\Scripts\activate

rem Pythonスクリプトを実行
venv\Scripts\Python.exe app.py
