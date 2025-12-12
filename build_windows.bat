@echo off
setlocal

echo ============================
echo ACTIVATING VENV
echo ============================
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate
) else (
  echo No .venv found. Please create venv first: python -m venv .venv
  pause
  exit /b 1
)

echo ============================
echo INSTALLING DEPENDENCIES
echo ============================
python -m pip install --upgrade pip
if exist "requirements.txt" (
  pip install -r requirements.txt
) else (
  echo Warning: requirements.txt not found. Continuing without installing deps.
)
pip install pyinstaller

echo ============================
echo CHECKING FFMPEG
echo ============================
if not exist "bundled_tools\ffmpeg\bin\ffmpeg.exe" (
   echo ERROR: ffmpeg.exe missing in bundled_tools\ffmpeg\bin
   echo Run PowerShell: pwsh -File .\ffmpeg_fetch.ps1
   pause
   exit /b 1
)

echo ============================
echo RUNNING PYINSTALLER
echo ============================
pyinstaller --noconfirm --onefile --windowed --clean ^
  --add-data "assets;assets" ^
  --add-data "bundled_tools/ffmpeg/bin/ffmpeg.exe;ffmpeg/bin" ^
  --add-data "bundled_tools/ffmpeg/bin/ffprobe.exe;ffmpeg/bin" ^
  --add-data "downloads;downloads" ^
  --add-data "output;output" ^
  --name ShortsStudio cli.py

echo ============================
echo BUILD FINISHED!
echo Check the dist folder: %cd%\dist\ShortsStudio.exe
pause
endlocal
