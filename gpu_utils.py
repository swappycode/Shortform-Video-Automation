# gpu_utils.py
# -*- coding: utf-8 -*-
"""
GPU Optimization Utilities for ShortsStudio
Provides GPU memory management, device info, and performance monitoring
"""

import torch
import subprocess
import json
from pathlib import Path

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False
    print("[WARN] pynvml not found. Install with: pip install nvidia-ml-py3")

def init_gpu():
    """Initialize GPU and display device info"""
    print("=" * 60)
    print("GPU INITIALIZATION")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        print("[WARN] CUDA is NOT available. Using CPU mode (slower).")
        print("[INFO] To enable GPU, install CUDA and proper drivers.")
        return False
    
    cuda_version = torch.version.cuda
    device_name = torch.cuda.get_device_name(0)
    device_count = torch.cuda.device_count()
    
    print(f"✓ CUDA Available: Yes")
    print(f"  Version: {cuda_version}")
    print(f"  Device Count: {device_count}")
    print(f"  Primary GPU: {device_name}")
    
    # Get memory info
    total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"  Total Memory: {total_memory:.2f} GB")
    
    print("=" * 60 + "\n")
    return True

def clear_gpu_cache():
    """Clear GPU cache to free memory"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

def get_gpu_memory_usage():
    """Get GPU memory usage in GB"""
    if not torch.cuda.is_available():
        return 0, 0
    
    allocated = torch.cuda.memory_allocated(0) / (1024**3)
    reserved = torch.cuda.memory_reserved(0) / (1024**3)
    return allocated, reserved

def print_gpu_memory():
    """Print formatted GPU memory usage"""
    if not torch.cuda.is_available():
        print("GPU not available")
        return
    
    allocated, reserved = get_gpu_memory_usage()
    total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    
    print(f"GPU Memory: {allocated:.2f}GB / {total:.2f}GB allocated, {reserved:.2f}GB reserved")

def get_gpu_temperature():
    """Get GPU temperature using nvidia-smi"""
    if not HAS_PYNVML:
        return None
    
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
        return temp
    except:
        return None

def get_gpu_utilization():
    """Get GPU utilization percentage"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        return float(result.stdout.strip())
    except:
        return None

def optimize_batch_size(model_size_gb, available_memory_pct=0.8):
    """
    Recommend batch size based on model and available memory
    
    Args:
        model_size_gb: Size of model in GB
        available_memory_pct: Percentage of GPU memory to use (0-1)
    
    Returns:
        Recommended batch size
    """
    if not torch.cuda.is_available():
        return 1
    
    total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    available = total_memory * available_memory_pct
    
    # Estimate: each item needs ~2x model size
    batch_size = int(available / (model_size_gb * 2))
    return max(1, batch_size)

def create_optimization_report():
    """Generate a GPU optimization report"""
    print("\n" + "=" * 60)
    print("GPU OPTIMIZATION REPORT")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        print("[WARNING] GPU not available - using CPU fallback")
        return
    
    # Device info
    device = torch.cuda.get_device_name(0)
    print(f"\n✓ GPU Device: {device}")
    print(f"✓ CUDA Version: {torch.version.cuda}")
    print(f"✓ PyTorch Version: {torch.__version__}")
    
    # Memory info
    total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"✓ Total GPU Memory: {total_mem:.2f} GB")
    
    # Temperature
    temp = get_gpu_temperature()
    if temp is not None:
        print(f"✓ Current Temperature: {temp}°C")
    
    # Optimization tips
    print("\n" + "=" * 60)
    print("OPTIMIZATION TIPS:")
    print("=" * 60)
    print("1. Layer 1: Uses GPU for audio FFT calculations (if CuPy installed)")
    print("   → Install: pip install cupy-cuda11x (replace 11x with your CUDA version)")
    print("   → Speeds up: Audio energy detection by ~5-10x")
    print("")
    print("2. Layer 2: Uses GPU for")
    print("   → Whisper transcription (float16 precision)")
    print("   → Frame difference calculation (PyTorch tensor ops)")
    print("   → Parallel processing with ThreadPoolExecutor")
    print("   → Speeds up: Content filtering by ~8-15x")
    print("")
    print("3. Layer 3: Uses GPU for")
    print("   → Whisper transcription (large-v3 model)")
    print("   → h264_nvenc hardware encoding (-preset fast)")
    print("   → CUDA hwaccel for video processing")
    print("   → Speeds up: Video rendering by ~10-20x")
    print("")
    print("4. Memory Management:")
    print("   → Automatic cache clearing between clips")
    print("   → float16 precision reduces memory by ~50%")
    print("   → Recommend 6GB+ GPU memory for optimal performance")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    init_gpu()
    create_optimization_report()
    print_gpu_memory()
