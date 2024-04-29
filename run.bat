@echo off

rem 初回は仮想環境を用意する

rem 仮想環境の有効化
call venv\Scripts\activate

rem Pythonスクリプトを実行
venv\Scripts\Python.exe main.py
