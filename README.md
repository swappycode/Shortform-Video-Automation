# ShortsStudio – Automated Short-Form Video Processing Pipeline

ShortsStudio is a standalone desktop application designed to automate the process of converting long-form video content into short-form, platform-ready clips.  
It provides a complete processing pipeline including YouTube downloading, audio event detection, AI-powered transcription and filtering, and final rendering with subtitles.

The software is written in Python, packaged into a single Windows executable using PyInstaller.  
FFmpeg is bundled automatically, and Whisper AI models are downloaded on first use.

---

## Table of Contents
1. Introduction  
2. Features  
3. Technology Stack  
4. System Requirements  
5. Installation  
6. GPU Acceleration  
7. Usage Guide (End Users)  
8. Pipeline Architecture  
9. Developer Guide  
10. Model Download Details  
11. Known Limitations  
12. Contributing  
13. License  

---

## 1. Introduction

ShortsStudio automates the process of generating short-form content from longer videos.  
It identifies interesting segments, transcribes speech using Whisper, filters content, generates subtitles, and renders final short-form clips.

The application is suitable for creators, editors, and automation developers.

---

## 2. Features

### Core Features
- Full YouTube video downloader (VOD or custom time segments)  
- Automated audio peak detection  
- Whisper transcription and content filtering  
- Subtitle generation and burn-in  
- Rendering optimized for vertical short-form output  
- Clean Tkinter-based GUI  
- Configuration save/load support  
- FFmpeg fully bundled  
- Whisper models auto-download on first run  
- No Python installation required  
- Fully standalone `.exe`

### Workflow Features
- Modular layer execution  
- Run each layer individually or execute the entire pipeline  
- Reproducible automated processing  
- Designed for extensibility  

---

## 3. Technology Stack

### Core Languages & Frameworks
- Python 3.10  
- Tkinter (GUI)  
- PyInstaller (packaging)

### Libraries
- `yt-dlp`  
- `pysubs2`  
- `faster-whisper`  
- `huggingface-hub`  
- `ffmpeg` (bundled)  

### AI Models
- Whisper Medium  
- Whisper Large-V3  

---

## 4. System Requirements

- Windows 10 / Windows 11  
- x64 architecture  
- Internet required only for first model download  
- Minimum 6 GB RAM for stable processing  
- 2–4 GB free disk space for model cache  

---

## 5. Installation

1. Download the latest `ShortsStudio.exe` from the Releases page.  
2. Place it anywhere on your system.  
3. Double-click to launch.  
4. On first run, Whisper models will download automatically.

No additional setup or Python installation is required.

---

## 6. GPU Acceleration

ShortsStudio uses `faster-whisper`, which supports NVIDIA CUDA GPUs.

### GPU is used when:
- A supported NVIDIA GPU is installed  
- CUDA Toolkit is installed  
- Drivers are properly configured  

### If GPU is unavailable:
Whisper transcription automatically falls back to CPU mode.  
All features remain functional, though inference may be slower.

---

## 7. Usage Guide (End Users)

### Step 1 — Launch the Application
Open `ShortsStudio.exe`.

### Step 2 — Choose the download mode:
- Full video / VOD  
- Custom segment  
- Live stream (if supported)

### Step 3 — Paste the YouTube URL

### Step 4 — Configure optional time range (for segment mode)

### Step 5 — Run the layers:
- **Layer 1**: Detect audio peaks  
- **Layer 2**: Transcribe + filter  
- **Layer 3**: Render final output  
- **Run All Layers**: Complete automation

### Step 6 — Locate output  
Final processed shorts are saved in the `output/` directory.

---

## 8. Pipeline Architecture

ShortsStudio uses a structured 3-layer architecture:

### Layer 1 — Audio Peak Detection
- Extracts and analyzes the waveform  
- Identifies loud or high-impact moments  
- Produces candidate timestamps

### Layer 2 — Whisper Transcription & Filtering
- Performs speech-to-text  
- Can filter based on keywords or logic  
- Outputs refined timestamps + subtitles  

### Layer 3 — Rendering & Subtitles
- Clips selected video segments  
- Generates subtitles  
- Uses FFmpeg to overlay subtitles  
- Produces `.mp4` short-form optimized output  

---

## 9. Developer Guide

### Project Structure
```
.
├── gui.py                     # GUI application
├── cli.py                     # Entrypoint for PyInstaller
├── layer1.py                  # Audio peak analysis
├── layer2.py                  # Whisper inference and filtering
├── layer3.py                  # Rendering and subtitle processing
├── downloader.py              # YouTube downloading logic
├── render.py                  # Rendering utilities and ffmpeg integration
└── requirements.txt
```

### Running Locally
Install dependencies:
```
pip install -r requirements.txt
```

Run GUI:
```
python gui.py
```

### Building the Executable
```
pyinstaller --onefile --windowed cli.py
```

CI workflow performs this automatically for production builds.

---

## 10. Model Download Details

Whisper models are downloaded automatically the first time Layer 2 is executed.  
Models are cached in:

```
C:\Users\<username>\.cache\huggingface\
```

This allows the executable to remain small while still supporting powerful AI models.

---

## 11. Known Limitations

- CPU mode is slower, especially for Whisper-Large  
- RAM usage increases with higher model sizes  
- Only Windows builds are currently provided  
- Long videos may require significant processing time  
- First model download requires internet access  

---

## 12. Contributing

Contributions are welcome.

You may:
- Report issues  
- Submit pull requests  
- Improve documentation  
- Add processing layers  
- Expand rendering options  
- Implement Linux/macOS support  

Standard GitHub contribution practices apply.

---

## 13. License

This project is licensed under the MIT License unless otherwise noted.
