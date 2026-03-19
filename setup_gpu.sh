#!/bin/bash
# setup_gpu.sh - Linux/macOS GPU setup script for ShortsStudio

echo ""
echo "==============================================="
echo "ShortsStudio GPU Setup"
echo "==============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

echo "[✓] Python $(python3 --version) found"
echo ""

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip3 is not available"
    exit 1
fi

echo "[✓] pip3 found"
echo ""

# Display CUDA check instructions
echo "============================================"
echo "Step 1: Verify CUDA Installation"
echo "============================================"
echo ""

if command -v nvidia-smi &> /dev/null; then
    echo "[✓] NVIDIA drivers detected"
    nvidia-smi
    echo ""
else
    echo "[WARNING] nvidia-smi not found. CUDA drivers may not be installed properly."
    echo "For GPU support, install CUDA from: https://developer.nvidia.com/cuda-downloads"
    echo ""
fi

# Install PyTorch
echo "============================================"
echo "Step 2: Installing PyTorch with CUDA"
echo "============================================"
echo ""
echo "Choose CUDA version:"
echo "1) CUDA 12.1 (recommended for new setups)"
echo "2) CUDA 11.8"
echo "3) CPU only (no GPU)"
echo ""
read -p "Enter choice (1-3): " cuda_choice

case $cuda_choice in
    1)
        echo "Installing PyTorch for CUDA 12.1..."
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        CUDA_VERSION="121"
        ;;
    2)
        echo "Installing PyTorch for CUDA 11.8..."
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        CUDA_VERSION="118"
        ;;
    *)
        echo "Installing PyTorch for CPU only..."
        pip3 install torch torchvision torchaudio
        CUDA_VERSION="cpu"
        ;;
esac

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install PyTorch"
    exit 1
fi

echo "[✓] PyTorch installed"
echo ""

# Install CuPy
if [ "$CUDA_VERSION" != "cpu" ]; then
    echo "Installing CuPy for CUDA $CUDA_VERSION..."
    if [ "$CUDA_VERSION" = "121" ]; then
        pip3 install cupy-cuda12x
    else
        pip3 install cupy-cuda11x
    fi
    
    if [ $? -ne 0 ]; then
        echo "[WARNING] Failed to install CuPy - CPU fallback will be used"
    else
        echo "[✓] CuPy installed"
    fi
else
    echo "Skipping CuPy (CPU mode selected)"
fi

echo ""

# Install other dependencies
echo "============================================"
echo "Step 3: Installing Dependencies"
echo "============================================"
echo ""
pip3 install -r requirement.txt

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo "[✓] All dependencies installed"
echo ""

# Verify installation
echo "============================================"
echo "Step 4: Verifying GPU Setup"
echo "============================================"
echo ""
python3 gpu_utils.py

echo ""
echo "============================================"
echo "[✓] Setup Complete!"
echo "============================================"
echo ""
echo "You can now run: python3 main.py"
echo ""
