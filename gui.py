import sys
import os
import subprocess
from pathlib import Path

# ---- Auto-Venv Relaucher ----
# This MUST run before any third-party imports (like customtkinter) to prevent ModuleNotFoundErrors 
# when users launch the script using their global Python environment instead of the .venv.
venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
if sys.platform == "win32" and venv_python.exists() and sys.executable.lower() != str(venv_python).lower():
    sys.exit(subprocess.call([str(venv_python)] + sys.argv))
# -----------------------------

# ---- Ensure UTF-8 Console ----
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- Bundled FFmpeg Setup ----
def prefer_bundled_ffmpeg():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    candidates = [
      os.path.join(base, "ffmpeg", "bin"),
      os.path.join(base, "bundled_tools", "ffmpeg", "bin")
    ]
    for ffbin in candidates:
        if os.path.isdir(ffbin):
            os.environ["PATH"] = ffbin + os.pathsep + os.environ.get("PATH", "")
            os.environ["FFMPEG_BINARY"] = os.path.join(ffbin, "ffmpeg.exe") if os.name=="nt" else os.path.join(ffbin,"ffmpeg")
            break
prefer_bundled_ffmpeg()

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import threading

# For font detection
if sys.platform == "win32":
    import winreg
elif sys.platform == "darwin":
    pass  # macOS fonts
else:
    pass  # Linux fonts

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ShortsAutomationGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("🎬 Shorts Studio - Automation Panel")
        self.geometry("1100x800")
        self.minsize(900, 600)
        
        # Config file path
        self.config_file = Path("config.json")
        
        # Default configuration
        self.config = {
            "layer1": {
                "sample_rate": 16000,
                "window": 0.25,
                "hop": 0.125,
                "sensitivity": 1.6,
                "pre_buffer": 1.5,
                "post_buffer": 8.0,
                "min_clip": 30.0,
                "max_clip": 60.0,
                "merge_window": 7.5
            },
            "layer2": {
                "keywords": "clip,bro,bruh,bru,wtf,holy,oh my god,omg,oh my gosh,what,wait,no,damn,brooo,nah,yo,fuck,freaking,dude,guys,wow,damn,shit,crazy,insane,unbelievable",
                "sample_fps": 2,
                "frame_diff_thresh": 0.12,
                "kw_threshold": 4,
                "vis_threshold": 70
            },
            "layer3": {
                "model_name": "large-v3",
                "font_name": "Komika Axis",
                "font_size": 18,
                "font_bold": True,
                "outline_width": 3,
                "primary_color": "&H00FFAA00",
                "outline_color": "&H00FFFFFF",
                "alignment": 2,
                "margin_v": 50,
                "max_text_length": 36,
                "bgm_volume": 0.3,
                "bgm_path": "assets/bgm.mp3",
                "ducking_threshold": 0.02,
                "ducking_ratio": 4,
                "ducking_attack": 200,
                "ducking_release": 1000,
                "audio_boost": 1.5
            }
        }
        
        # Load existing config if available
        self.load_config_silent()
        
        # Get available fonts and models
        self.available_fonts = self.get_system_fonts()
        self.available_models = self.get_whisper_models()
        
        # ---- UI Layout Setup ----
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.create_sidebar()
        self.create_main_area()
        self.create_console_area()
        
        # Create the views
        self.views = {
            "downloader": self.create_downloader_view(),
            "layer1": self.create_layer1_view(),
            "layer2": self.create_layer2_view(),
            "layer3": self.create_layer3_view()
        }
        
        # Initialize default view
        self.select_view("downloader")
        
        # Log after UI is ready
        self.log("✅ CustomTkinter GUI Loaded Successfully!")

    # --- System Query Methods ---
    def get_system_fonts(self):
        fonts = set()
        if sys.platform == "win32":
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    font_name = name.split("(")[0].strip()
                    fonts.add(font_name)
                winreg.CloseKey(key)
            except Exception as e:
                print(f"Could not read Windows fonts: {e}")
        # Add basic fallbacks
        common_fonts = ["Arial", "Courier New", "Verdana", "Impact", "Komika Axis", "Bangers"]
        fonts.update(common_fonts)
        return sorted(list(fonts))
    
    def get_whisper_models(self):
        models = [
            "tiny", "tiny.en", "base", "base.en", "small", "small.en", 
            "medium", "medium.en", "large-v1", "large-v2", "large-v3"
        ]
        return models

    # --- GUI Construction ---
    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) # spacer
        
        logo_label = ctk.CTkLabel(self.sidebar_frame, text="Shorts Studio", 
                                  font=ctk.CTkFont(size=20, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation Buttons
        self.btn_downloader = ctk.CTkButton(self.sidebar_frame, text="🎬 Downloader", 
                                           corner_radius=8, height=40, font=ctk.CTkFont(size=14),
                                           fg_color="transparent", hover_color=("gray70", "gray30"),
                                           anchor="w", command=lambda: self.select_view("downloader"))
        self.btn_downloader.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_layer1 = ctk.CTkButton(self.sidebar_frame, text="🔉 L1: Audio Peaks", 
                                           corner_radius=8, height=40, font=ctk.CTkFont(size=14),
                                           fg_color="transparent", hover_color=("gray70", "gray30"),
                                           anchor="w", command=lambda: self.select_view("layer1"))
        self.btn_layer1.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_layer2 = ctk.CTkButton(self.sidebar_frame, text="brain L2: AI Filter", 
                                           corner_radius=8, height=40, font=ctk.CTkFont(size=14),
                                           fg_color="transparent", hover_color=("gray70", "gray30"),
                                           anchor="w", command=lambda: self.select_view("layer2"))
        self.btn_layer2.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_layer3 = ctk.CTkButton(self.sidebar_frame, text="🎞️ L3: Render", 
                                           corner_radius=8, height=40, font=ctk.CTkFont(size=14),
                                           fg_color="transparent", hover_color=("gray70", "gray30"),
                                           anchor="w", command=lambda: self.select_view("layer3"))
        self.btn_layer3.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        # Actions
        action_label = ctk.CTkLabel(self.sidebar_frame, text="Configuration", 
                                  font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        action_label.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="w")
        
        ctk.CTkButton(self.sidebar_frame, text="💾 Save Config", command=self.save_config,
                      fg_color="#3B82F6", hover_color="#2563EB").grid(row=8, column=0, padx=20, pady=5, sticky="ew")
        ctk.CTkButton(self.sidebar_frame, text="📂 Load Config", command=self.load_config_dialog,
                      fg_color="transparent", border_width=1).grid(row=9, column=0, padx=20, pady=5, sticky="ew")
        
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 20), sticky="ew")
        
    def create_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
    def create_console_area(self):
        self.console_frame = ctk.CTkFrame(self, height=200)
        self.console_frame.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="sew")
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)
        
        # Run All Layers Button
        top_bar = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(top_bar, text="Console Output", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.btn_run_all = ctk.CTkButton(top_bar, text="⚡ RUN ALL LAYERS", fg_color="#10B981", 
                                         hover_color="#059669", font=ctk.CTkFont(weight="bold"),
                                         command=self.run_all_layers)
        self.btn_run_all.grid(row=0, column=2, sticky="e")
        
        # Console Log
        self.console = ctk.CTkTextbox(self.console_frame, wrap="word", font=("Consolas", 12))
        self.console.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

    def select_view(self, name):
        # Update button highlighting
        for btn in [self.btn_downloader, self.btn_layer1, self.btn_layer2, self.btn_layer3]:
            btn.configure(fg_color="transparent")
            
        if name == "downloader": self.btn_downloader.configure(fg_color=("gray75", "gray25"))
        elif name == "layer1": self.btn_layer1.configure(fg_color=("gray75", "gray25"))
        elif name == "layer2": self.btn_layer2.configure(fg_color=("gray75", "gray25"))
        elif name == "layer3": self.btn_layer3.configure(fg_color=("gray75", "gray25"))
        
        # Show correct frame
        for view_name, frame in self.views.items():
            if view_name == name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    # --- Downloader View ---
    def create_downloader_view(self):
        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        
        ctk.CTkLabel(frame, text="YouTube Downloader", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 20))
        
        # URL
        url_frame = ctk.CTkFrame(frame)
        url_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(url_frame, text="Video URL", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))
        self.youtube_url = ctk.CTkEntry(url_frame, placeholder_text="https://www.youtube.com/watch?v=...")
        self.youtube_url.pack(fill="x", padx=15, pady=10)
        
        # Download Mode
        mode_frame = ctk.CTkFrame(frame)
        mode_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(mode_frame, text="Mode Select", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.download_mode = ctk.StringVar(value="full")
        ctk.CTkRadioButton(mode_frame, text="Full Video/VOD", variable=self.download_mode, value="full").pack(anchor="w", padx=15, pady=5)
        ctk.CTkRadioButton(mode_frame, text="Video Segment (Time Range)", variable=self.download_mode, value="segment").pack(anchor="w", padx=15, pady=5)
        ctk.CTkRadioButton(mode_frame, text="Live Stream", variable=self.download_mode, value="live").pack(anchor="w", padx=15, pady=(5, 10))
        
        # Time Options
        time_frame = ctk.CTkFrame(frame)
        time_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(time_frame, text="Start Time (HH:MM:SS)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")
        self.start_time = ctk.CTkEntry(time_frame)
        self.start_time.insert(0, "0:00:00")
        self.start_time.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(time_frame, text="End Time (HH:MM:SS) (optional)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=15, pady=(10, 0), sticky="w")
        self.end_time = ctk.CTkEntry(time_frame)
        self.end_time.grid(row=1, column=1, padx=15, pady=(0, 10), sticky="ew")
        
        time_frame.grid_columnconfigure(0, weight=1)
        time_frame.grid_columnconfigure(1, weight=1)
        
        # Download Button
        btn = ctk.CTkButton(frame, text="📥 Download to vod.mp4", font=ctk.CTkFont(size=15, weight="bold"),
                            height=45, fg_color="#3B82F6", hover_color="#2563EB", command=self.start_download)
        btn.pack(pady=20)
        
        return frame

    # --- Helper for UI generation ---
    def add_entry_row(self, parent, label_text, layer, key, row):
        ctk.CTkLabel(parent, text=label_text).grid(row=row, column=0, padx=15, pady=10, sticky="w")
        entry = ctk.CTkEntry(parent, width=150)
        entry.insert(0, str(self.config[layer][key]))
        entry.grid(row=row, column=1, padx=15, pady=10, sticky="e")
        setattr(self, f"{layer}_{key}", entry)
        
    # --- Layer 1 View ---
    def create_layer1_view(self):
        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="Layer 1: Audio Peak Detection", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="▶ Run Layer 1", width=120, command=lambda: self.run_layer(1)).pack(side="right")
        
        # Params 1
        p1 = ctk.CTkFrame(frame)
        p1.pack(fill="x", pady=10)
        p1.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(p1, text="Audio Detection", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        self.add_entry_row(p1, "Sample Rate (Hz)", "layer1", "sample_rate", 1)
        self.add_entry_row(p1, "Window Size (s)", "layer1", "window", 2)
        self.add_entry_row(p1, "Hop Size (s)", "layer1", "hop", 3)
        self.add_entry_row(p1, "Sensitivity Multiplier", "layer1", "sensitivity", 4)
        
        # Params 2
        p2 = ctk.CTkFrame(frame)
        p2.pack(fill="x", pady=10)
        p2.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(p2, text="Clip Timings", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        self.add_entry_row(p2, "Pre-buffer (s)", "layer1", "pre_buffer", 1)
        self.add_entry_row(p2, "Post-buffer (s)", "layer1", "post_buffer", 2)
        self.add_entry_row(p2, "Min Clip Duration (s)", "layer1", "min_clip", 3)
        self.add_entry_row(p2, "Max Clip Duration (s)", "layer1", "max_clip", 4)
        self.add_entry_row(p2, "Merge Window (s)", "layer1", "merge_window", 5)
        
        return frame

    # --- Layer 2 View ---
    def create_layer2_view(self):
        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="Layer 2: Whisper Filtering", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="▶ Run Layer 2", width=120, command=lambda: self.run_layer(2)).pack(side="right")
        
        p1 = ctk.CTkFrame(frame)
        p1.pack(fill="x", pady=10)
        ctk.CTkLabel(p1, text="Keyword Settings", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))
        
        self.layer2_keywords = ctk.CTkTextbox(p1, height=100)
        self.layer2_keywords.pack(fill="x", padx=15, pady=10)
        self.layer2_keywords.insert("1.0", self.config["layer2"]["keywords"])
        
        grid_f = ctk.CTkFrame(p1, fg_color="transparent")
        grid_f.pack(fill="x")
        grid_f.grid_columnconfigure(1, weight=1)
        self.add_entry_row(grid_f, "Keyword Threshold", "layer2", "kw_threshold", 0)
        
        p2 = ctk.CTkFrame(frame)
        p2.pack(fill="x", pady=10)
        p2.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(p2, text="Visual Analysis", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        self.add_entry_row(p2, "Sample FPS", "layer2", "sample_fps", 1)
        self.add_entry_row(p2, "Frame Diff Threshold", "layer2", "frame_diff_thresh", 2)
        self.add_entry_row(p2, "Visual Target Threshold", "layer2", "vis_threshold", 3)
        
        return frame

    # --- Layer 3 View ---
    def create_layer3_view(self):
        frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="Layer 3: Render & Subtitles", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="▶ Run Layer 3", width=120, command=lambda: self.run_layer(3)).pack(side="right")
        
        # Typography & Subtitles
        p1 = ctk.CTkFrame(frame)
        p1.pack(fill="x", pady=10)
        p1.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(p1, text="Typography & Whisper", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        
        ctk.CTkLabel(p1, text="Transcription Model").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.layer3_model_name = ctk.CTkComboBox(p1, values=self.available_models, width=200)
        self.layer3_model_name.set(self.config["layer3"]["model_name"])
        self.layer3_model_name.grid(row=1, column=1, padx=15, pady=10, sticky="e")
        
        ctk.CTkLabel(p1, text="Font Family").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.layer3_font_name = ctk.CTkComboBox(p1, values=self.available_fonts, width=200)
        self.layer3_font_name.set(self.config["layer3"]["font_name"])
        self.layer3_font_name.grid(row=2, column=1, padx=15, pady=10, sticky="e")
        
        self.add_entry_row(p1, "Font Size", "layer3", "font_size", 3)
        
        ctk.CTkLabel(p1, text="Bold Typography").grid(row=4, column=0, padx=15, pady=10, sticky="w")
        self.layer3_font_bold_var = ctk.BooleanVar(value=self.config["layer3"]["font_bold"])
        self.layer3_font_bold = ctk.CTkSwitch(p1, text="", variable=self.layer3_font_bold_var)
        self.layer3_font_bold.grid(row=4, column=1, padx=15, pady=10, sticky="e")
        
        self.add_entry_row(p1, "Outline Width", "layer3", "outline_width", 5)
        self.add_entry_row(p1, "Primary Color (ASS)", "layer3", "primary_color", 6)
        self.add_entry_row(p1, "Outline Color (ASS)", "layer3", "outline_color", 7)
        self.add_entry_row(p1, "Alignment (1-9)", "layer3", "alignment", 8)
        self.add_entry_row(p1, "Margin Vertical", "layer3", "margin_v", 9)
        self.add_entry_row(p1, "Max Text Length", "layer3", "max_text_length", 10)
        
        # Audio
        p2 = ctk.CTkFrame(frame)
        p2.pack(fill="x", pady=10)
        p2.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(p2, text="Mixer & Audio Ducking", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        
        ctk.CTkLabel(p2, text="BGM Target File").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        file_f = ctk.CTkFrame(p2, fg_color="transparent")
        file_f.grid(row=1, column=1, padx=15, pady=10, sticky="e")
        self.layer3_bgm_path = ctk.CTkEntry(file_f, width=200)
        self.layer3_bgm_path.insert(0, self.config["layer3"]["bgm_path"])
        self.layer3_bgm_path.pack(side="left", padx=(0, 5))
        ctk.CTkButton(file_f, text="Browse", width=60, command=self.browse_bgm).pack(side="left")
        
        self.add_entry_row(p2, "Vocals Boost Multiplier", "layer3", "audio_boost", 2)
        self.add_entry_row(p2, "BGM Main Volume", "layer3", "bgm_volume", 3)
        self.add_entry_row(p2, "Ducking Threshold", "layer3", "ducking_threshold", 4)
        self.add_entry_row(p2, "Ducking Ratio", "layer3", "ducking_ratio", 5)
        self.add_entry_row(p2, "Ducking Attack (ms)", "layer3", "ducking_attack", 6)
        self.add_entry_row(p2, "Ducking Release (ms)", "layer3", "ducking_release", 7)
        
        return frame

    def browse_bgm(self):
        filename = filedialog.askopenfilename(
            title="Select BGM", 
            filetypes=[("Audio", "*.mp3 *.wav *.m4a")]
        )
        if filename:
            self.layer3_bgm_path.delete(0, tk.END)
            self.layer3_bgm_path.insert(0, filename)

    # --- Save/Load & State Management ---
    def collect_config(self):
        try:
            config = {
                "layer1": {
                    "sample_rate": int(self.layer1_sample_rate.get()),
                    "window": float(self.layer1_window.get()),
                    "hop": float(self.layer1_hop.get()),
                    "sensitivity": float(self.layer1_sensitivity.get()),
                    "pre_buffer": float(self.layer1_pre_buffer.get()),
                    "post_buffer": float(self.layer1_post_buffer.get()),
                    "min_clip": float(self.layer1_min_clip.get()),
                    "max_clip": float(self.layer1_max_clip.get()),
                    "merge_window": float(self.layer1_merge_window.get())
                },
                "layer2": {
                    "keywords": self.layer2_keywords.get("1.0", tk.END).strip(),
                    "sample_fps": int(self.layer2_sample_fps.get()),
                    "frame_diff_thresh": float(self.layer2_frame_diff_thresh.get()),
                    "kw_threshold": int(self.layer2_kw_threshold.get()),
                    "vis_threshold": float(self.layer2_vis_threshold.get())
                },
                "layer3": {
                    "model_name": self.layer3_model_name.get(),
                    "font_name": self.layer3_font_name.get(),
                    "font_size": int(self.layer3_font_size.get()),
                    "font_bold": self.layer3_font_bold_var.get(),
                    "outline_width": int(self.layer3_outline_width.get()),
                    "primary_color": self.layer3_primary_color.get(),
                    "outline_color": self.layer3_outline_color.get(),
                    "alignment": int(self.layer3_alignment.get()),
                    "margin_v": int(self.layer3_margin_v.get()),
                    "max_text_length": int(self.layer3_max_text_length.get()),
                    "bgm_volume": float(self.layer3_bgm_volume.get()),
                    "bgm_path": self.layer3_bgm_path.get(),
                    "ducking_threshold": float(self.layer3_ducking_threshold.get()),
                    "ducking_ratio": int(self.layer3_ducking_ratio.get()),
                    "ducking_attack": int(self.layer3_ducking_attack.get()),
                    "ducking_release": int(self.layer3_ducking_release.get()),
                    "audio_boost": float(self.layer3_audio_boost.get())
                }
            }
            return config
        except Exception as e:
            self.log(f"❌ Error collecting config values: {e}")
            return None

    def save_config(self):
        config = self.collect_config()
        if not config: return
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            self.log("✅ Configuration saved successfully!")
            # Avoid annoying popups for minor actions in custom UIs. Console is enough.
        except Exception as e:
            self.log(f"❌ Error saving config: {e}")

    def load_config_silent(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    for layer in self.config:
                        if layer in loaded_config:
                            for key in self.config[layer]:
                                if key in loaded_config[layer]:
                                    self.config[layer][key] = loaded_config[layer][key]
        except Exception:
            pass

    def load_config_dialog(self):
        filename = filedialog.askopenfilename(title="Load Config", filetypes=[("JSON Files", "*.json")])
        if filename:
            try:
                with open(filename, 'r') as f:
                    new_conf = json.load(f)
                with open(self.config_file, 'w') as f:
                    json.dump(new_conf, f, indent=4)
                self.log(f"✅ Configuration replaced from {filename}. Please restart to apply.")
                messagebox.showinfo("Restart Required", "Config loaded! Please close and reopen the app.")
            except Exception as e:
                self.log(f"❌ Error loading config: {e}")

    # --- Actions ---
    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.update()

    def _run_process(self, cmd_args, success_msg):
        try:
            process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace')
            for line in process.stdout:
                self.log(line.rstrip())
            process.wait()
            if process.returncode == 0 or process.returncode == 3221226505:
                self.log(f"\n✅ {success_msg}")
            else:
                self.log(f"\n❌ Process failed with return code {process.returncode}")
        except Exception as e:
            self.log(f"\n❌ Execution Error: {e}")

    def start_download(self):
        url = self.youtube_url.get().strip()
        mode = self.download_mode.get()
        if not url: return self.log("❌ Enter a valid URL!")
        
        self.log(f"\n{'='*40}\n📥 Downloading: {mode}\n{'='*40}")
        
        cmd = [sys.executable, "downloader.py", url]
        if mode == "segment":
            start, end = self.start_time.get().strip(), self.end_time.get().strip()
            if not start: return self.log("❌ Need start time!")
            cmd.append(start)
            if end: cmd.append(end)
        elif mode == "live":
            cmd.append("--live")
            
        threading.Thread(target=self._run_process, args=(cmd, "Download Done!"), daemon=True).start()

    def run_layer(self, layer_num):
        self.save_config()
        self.log(f"\n{'='*40}\n🚀 Running Layer {layer_num}\n{'='*40}")
        cmd = [sys.executable, f"layer{layer_num}.py"]
        threading.Thread(target=self._run_process, args=(cmd, f"Layer {layer_num} Completed!"), daemon=True).start()

    def run_all_layers(self):
        self.save_config()
        def runner():
            for layer in [1, 2, 3]:
                self.log(f"\n{'='*40}\n🚀 LAYER {layer}\n{'='*40}")
                try:
                    p = subprocess.Popen([sys.executable, f"layer{layer}.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace')
                    for line in p.stdout: self.log(line.rstrip())
                    p.wait()
                    if p.returncode != 0 and p.returncode != 3221226505:
                        self.log(f"\n❌ HALTING. Layer {layer} failed!")
                        return
                except Exception as e:
                    self.log(f"❌ Error: {e}"); return
            self.log(f"\n✅ ALL LAYERS DONE!")
        threading.Thread(target=runner, daemon=True).start()

if __name__ == "__main__":
    app = ShortsAutomationGUI()
    app.mainloop()