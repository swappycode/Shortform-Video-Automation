@echo off
REM setup_gpu.bat - Windows GPU setup script for ShortsStudio

echo.
echo ===============================================
echo ShortsStudio GPU Setup for Windows
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [✓] Python found
echo.

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available
    pause
    exit /b 1
)

echo [✓] pip found
echo.

REM Display CUDA check instructions
echo ============================================
echo Step 1: Verify CUDA Installation
echo ============================================
echo.
echo Checking for NVIDIA drivers...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] nvidia-smi not found. CUDA drivers may not be installed properly.
    echo Download from: https://developer.nvidia.com/cuda-downloads
    echo.
) else (
    echo [✓] NVIDIA drivers detected
    nvidia-smi
    echo.
)

REM Install PyTorch
echo ============================================
echo Step 2: Installing PyTorch with CUDA
echo ============================================
echo.
echo Choose CUDA version:
echo 1) CUDA 12.1 (recommended for new setups)
echo 2) CUDA 11.8
echo 3) CPU only (no GPU)
echo.
set /p cuda_choice="Enter choice (1-3): "

if "%cuda_choice%"=="1" (
    echo Installing PyTorch for CUDA 12.1...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
) else if "%cuda_choice%"=="2" (
    echo Installing PyTorch for CUDA 11.8...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Installing PyTorch for CPU only...
    pip install torch torchvision torchaudio
)

if errorlevel 1 (
    echo [ERROR] Failed to install PyTorch
    pause
    exit /b 1
)

echo [✓] PyTorch installed
echo.

REM Install CuPy
if "%cuda_choice%"=="1" (
    echo Installing CuPy for CUDA 12.1...
    pip install cupy-cuda12x
) else if "%cuda_choice%"=="2" (
    echo Installing CuPy for CUDA 11.8...
    pip install cupy-cuda11x
) else (
    echo Skipping CuPy (CPU mode selected)
    goto skip_cupy
)

if errorlevel 1 (
    echo [WARNING] Failed to install CuPy - CPU fallback will be used
)

:skip_cupy
echo.

REM Install other dependencies
echo ============================================
echo Step 3: Installing Dependencies
echo ============================================
echo.
pip install -r requirement.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [✓] All dependencies installed
echo.

REM Verify installation
echo ============================================
echo Step 4: Verifying GPU Setup
echo ============================================
echo.
python gpu_utils.py

echo.
echo ============================================
echo [✓] Setup Complete!
echo ============================================
echo.
echo You can now run: python main.py
echo.
pause
