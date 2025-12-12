@echo off
setlocal
set APPDIR=%~dp0
set MROOT=%ProgramData%\ShortsStudio\models
echo Creating model folder: %MROOT%
mkdir "%MROOT%" 2>NUL

echo Setting HF_HOME (session) to %MROOT%
set HF_HOME=%MROOT%

echo Ensure huggingface-hub is installed...
python -m pip install --upgrade pip
python -m pip install huggingface-hub

echo Running downloader to fetch large-v3 and medium...
python "%APPDIR%download_models.py" --dest "%MROOT%"

if %ERRORLEVEL% NEQ 0 (
  echo Model download failed. Please run:
  echo python "%APPDIR%download_models.py" --dest "%MROOT%"
) else (
  echo Models downloaded successfully to %MROOT%
)

pause
endlocal
