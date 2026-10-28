@echo off
REM Construit DeGaulleMan.exe (Windows) avec PyInstaller
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name DeGaulleMan --icon assets\icon.ico degaulleman.py
copy /Y dist\DeGaulleMan.exe DeGaulleMan.exe
