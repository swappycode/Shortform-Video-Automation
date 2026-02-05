import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
from pathlib import Path
import subprocess
import threading
import os
import sys

# For font detection
if sys.platform == "win32":
    import winreg
elif sys.platform == "darwin":
    pass  # macOS fonts
else:
    pass  # Linux fonts

class ShortsAutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Shorts Automation Control Panel")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
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
        
        # Load existing config if available (silently, before UI is created)
        self.load_config_silent()
        
        # Get available fonts and models
        self.available_fonts = self.get_system_fonts()
        self.available_models = self.get_whisper_models()
        
        # Create UI
        self.create_ui()
        
        # Log after UI is ready
        self.log("✅ GUI Loaded Successfully!")
        
    def get_system_fonts(self):
        """Get list of installed fonts on the system"""
        fonts = set()
        
        if sys.platform == "win32":
            # Windows fonts
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
                
        elif sys.platform == "darwin":
            # macOS fonts
            font_dirs = [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    for f in os.listdir(font_dir):
                        if f.endswith(('.ttf', '.otf', '.ttc')):
                            fonts.add(f.replace('.ttf', '').replace('.otf', '').replace('.ttc', ''))
                            
        else:
            # Linux fonts
            font_dirs = [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts")
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    for root, dirs, files in os.walk(font_dir):
                        for f in files:
                            if f.endswith(('.ttf', '.otf')):
                                fonts.add(f.replace('.ttf', '').replace('.otf', ''))
        
        # Add some common fonts as fallback
        common_fonts = ["Arial", "Times New Roman", "Courier New", "Verdana", 
                       "Georgia", "Comic Sans MS", "Impact", "Trebuchet MS",
                       "Komika Axis", "Bangers", "Bebas Neue"]
        fonts.update(common_fonts)
        
        return sorted(list(fonts))
    
    def get_whisper_models(self):
        """Get available Whisper models"""
        models = [
            "tiny", "tiny.en",
            "base", "base.en",
            "small", "small.en",
            "medium", "medium.en",
            "large-v1", "large-v2", "large-v3"
        ]
        
        # Check HF_HOME directory for downloaded models
        hf_home = os.environ.get("HF_HOME", "")
        if hf_home and os.path.exists(hf_home):
            try:
                model_dirs = os.listdir(hf_home)
                # Add any found models
                for d in model_dirs:
                    if "whisper" in d.lower():
                        models.append(d)
            except:
                pass
        
        return models
        
    def create_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = tk.Label(main_frame, text="🎬 Shorts Automation Control Panel", 
                               font=("Arial", 20, "bold"), bg="#667eea", fg="white", 
                               pady=15)
        title_label.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Create tabs
        self.create_downloader_tab()
        self.create_layer1_tab()
        self.create_layer2_tab()
        self.create_layer3_tab()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Buttons
        ttk.Button(button_frame, text="💾 Save Config", 
                   command=self.save_config, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📂 Load Config", 
                   command=self.load_config_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reset to Default", 
                   command=self.reset_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🚀 Run Layer 1", 
                   command=lambda: self.run_layer(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🚀 Run Layer 2", 
                   command=lambda: self.run_layer(2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🚀 Run Layer 3", 
                   command=lambda: self.run_layer(3)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="⚡ Run All Layers", 
                   command=self.run_all_layers, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        
        # Console output
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(3, weight=1)
        
        self.console = scrolledtext.ScrolledText(console_frame, height=10, wrap=tk.WORD, 
                                                  font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Style configuration
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
        
    def create_downloader_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="📥 YouTube Downloader")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Download Mode Selection
        frame1 = ttk.LabelFrame(scrollable_frame, text="Download Mode", padding="10")
        frame1.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        self.download_mode = tk.StringVar(value="full")
        
        ttk.Radiobutton(frame1, text="📺 Full Video/VOD", variable=self.download_mode, 
                       value="full").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Radiobutton(frame1, text="✂️ Video Segment (Time Range)", variable=self.download_mode, 
                       value="segment").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Radiobutton(frame1, text="🔴 Live Stream", variable=self.download_mode, 
                       value="live").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # URL Input
        frame2 = ttk.LabelFrame(scrollable_frame, text="YouTube URL", padding="10")
        frame2.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        tk.Label(frame2, text="URL:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.youtube_url = ttk.Entry(frame2, width=60)
        self.youtube_url.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.youtube_url.insert(0, "https://www.youtube.com/watch?v=...")
        
        # Time Range (for segment mode)
        frame3 = ttk.LabelFrame(scrollable_frame, text="Time Range (for Segment Mode)", padding="10")
        frame3.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        tk.Label(frame3, text="Start Time (HH:MM:SS or seconds):", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.start_time = ttk.Entry(frame3, width=30)
        self.start_time.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.start_time.insert(0, "0:00:00")
        
        tk.Label(frame3, text="End Time (HH:MM:SS or seconds, optional):", font=("Arial", 10)).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.end_time = ttk.Entry(frame3, width=30)
        self.end_time.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        self.end_time.insert(0, "")
        
        # Live Stream Duration (for live mode)
        frame4 = ttk.LabelFrame(scrollable_frame, text="Live Stream Options", padding="10")
        frame4.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        tk.Label(frame4, text="Max Duration (seconds, optional):", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.live_duration = ttk.Entry(frame4, width=30)
        self.live_duration.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.live_duration.insert(0, "")
        
        tk.Label(frame4, text="Leave empty to record entire stream", 
                font=("Arial", 9, "italic"), foreground="gray").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        
        # Download Button
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.grid(row=4, column=0, pady=20)
        
        ttk.Button(btn_frame, text="📥 Download to vod.mp4", 
                  command=self.start_download, style="Accent.TButton").pack(pady=10)
        
        # Info
        info_frame = ttk.LabelFrame(scrollable_frame, text="ℹ️ Information", padding="10")
        info_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        info_text = """• Downloads saved to downloads/ folder with timestamps
• Also copied to vod.mp4 for immediate processing
• Make sure yt-dlp is installed: pip install yt-dlp
• Time format examples: 1:30:00 (1h 30m), 90:00 (90 minutes), 5400 (seconds)
• For live streams, the download will wait for the stream to start
• Segment mode works with both live streams and VODs"""
        
        tk.Label(info_frame, text=info_text, justify=tk.LEFT, 
                font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_layer1_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Layer 1: Audio Peak Detection")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Audio Detection Parameters
        frame1 = ttk.LabelFrame(scrollable_frame, text="Audio Detection Parameters", padding="10")
        frame1.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        row = 0
        self.create_entry(frame1, "Sample Rate (Hz):", "layer1", "sample_rate", row)
        row += 1
        self.create_entry(frame1, "Window Size (seconds):", "layer1", "window", row)
        row += 1
        self.create_entry(frame1, "Hop Size (seconds):", "layer1", "hop", row)
        row += 1
        self.create_entry(frame1, "Sensitivity Multiplier:", "layer1", "sensitivity", row)
        
        # Clip Timing Parameters
        frame2 = ttk.LabelFrame(scrollable_frame, text="Clip Timing Parameters", padding="10")
        frame2.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        row = 0
        self.create_entry(frame2, "Pre-buffer (seconds):", "layer1", "pre_buffer", row)
        row += 1
        self.create_entry(frame2, "Post-buffer (seconds):", "layer1", "post_buffer", row)
        row += 1
        self.create_entry(frame2, "Min Clip Duration (seconds):", "layer1", "min_clip", row)
        row += 1
        self.create_entry(frame2, "Max Clip Duration (seconds):", "layer1", "max_clip", row)
        row += 1
        self.create_entry(frame2, "Merge Window (seconds):", "layer1", "merge_window", row)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_layer2_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Layer 2: Content Filtering")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Keyword Detection
        frame1 = ttk.LabelFrame(scrollable_frame, text="Keyword Detection", padding="10")
        frame1.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        tk.Label(frame1, text="Keywords (comma-separated):", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.layer2_keywords = tk.Text(frame1, height=5, width=60, wrap=tk.WORD)
        self.layer2_keywords.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.layer2_keywords.insert("1.0", self.config["layer2"]["keywords"])
        
        tk.Label(frame1, text="Keyword Threshold (min count):", font=("Arial", 10)).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.layer2_kw_threshold = ttk.Entry(frame1)
        self.layer2_kw_threshold.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        self.layer2_kw_threshold.insert(0, str(self.config["layer2"]["kw_threshold"]))
        
        # Visual Analysis
        frame2 = ttk.LabelFrame(scrollable_frame, text="Visual Analysis Parameters", padding="10")
        frame2.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        row = 0
        self.create_entry(frame2, "Sample FPS:", "layer2", "sample_fps", row)
        row += 1
        self.create_entry(frame2, "Frame Difference Threshold:", "layer2", "frame_diff_thresh", row)
        row += 1
        self.create_entry(frame2, "Visual Score Threshold:", "layer2", "vis_threshold", row)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_layer3_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Layer 3: Rendering & Subtitles")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Model Settings
        frame1 = ttk.LabelFrame(scrollable_frame, text="Transcription Model", padding="10")
        frame1.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        tk.Label(frame1, text="Model Name:", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.layer3_model_name = ttk.Combobox(frame1, values=self.available_models, width=27)
        self.layer3_model_name.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.layer3_model_name.set(self.config["layer3"]["model_name"])
        
        # Font Settings
        frame2 = ttk.LabelFrame(scrollable_frame, text="Font Settings", padding="10")
        frame2.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        row = 0
        tk.Label(frame2, text="Font Name:", font=("Arial", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.layer3_font_name = ttk.Combobox(frame2, values=self.available_fonts, width=27)
        self.layer3_font_name.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.layer3_font_name.set(self.config["layer3"]["font_name"])
        
        row += 1
        self.create_entry(frame2, "Font Size:", "layer3", "font_size", row)
        row += 1
        
        tk.Label(frame2, text="Bold:", font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, pady=5)
        self.layer3_font_bold = ttk.Checkbutton(frame2)
        self.layer3_font_bold.grid(row=row, column=1, sticky=tk.W, pady=5)
        if self.config["layer3"]["font_bold"]:
            self.layer3_font_bold.state(['selected'])
        row += 1
        
        self.create_entry(frame2, "Outline Width:", "layer3", "outline_width", row)
        row += 1
        self.create_entry(frame2, "Primary Color (ASS format):", "layer3", "primary_color", row)
        row += 1
        self.create_entry(frame2, "Outline Color (ASS format):", "layer3", "outline_color", row)
        row += 1
        self.create_entry(frame2, "Alignment (1-9):", "layer3", "alignment", row)
        row += 1
        self.create_entry(frame2, "Margin Vertical:", "layer3", "margin_v", row)
        row += 1
        self.create_entry(frame2, "Max Text Length (chars):", "layer3", "max_text_length", row)
        
        # Audio Settings
        frame3 = ttk.LabelFrame(scrollable_frame, text="Audio Settings", padding="10")
        frame3.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        self.create_entry(frame3, "Audio Boost (1.0 = normal, 1.5 = 50% louder):", "layer3", "audio_boost", 0)
        
        # Background Music Settings
        frame4 = ttk.LabelFrame(scrollable_frame, text="Background Music & Ducking", padding="10")
        frame4.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        tk.Label(frame4, text="BGM Path:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        bgm_frame = ttk.Frame(frame4)
        bgm_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.layer3_bgm_path = ttk.Entry(bgm_frame, width=40)
        self.layer3_bgm_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.layer3_bgm_path.insert(0, self.config["layer3"]["bgm_path"])
        
        ttk.Button(bgm_frame, text="Browse", command=self.browse_bgm).pack(side=tk.LEFT)
        
        row = 2
        self.create_entry(frame4, "BGM Volume (0.0-1.0):", "layer3", "bgm_volume", row)
        row += 1
        self.create_entry(frame4, "Ducking Threshold:", "layer3", "ducking_threshold", row)
        row += 1
        self.create_entry(frame4, "Ducking Ratio:", "layer3", "ducking_ratio", row)
        row += 1
        self.create_entry(frame4, "Ducking Attack (ms):", "layer3", "ducking_attack", row)
        row += 1
        self.create_entry(frame4, "Ducking Release (ms):", "layer3", "ducking_release", row)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_entry(self, parent, label_text, layer, key, row):
        tk.Label(parent, text=label_text, font=("Arial", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=5)
        entry = ttk.Entry(parent, width=30)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        entry.insert(0, str(self.config[layer][key]))
        setattr(self, f"{layer}_{key}", entry)
        parent.columnconfigure(1, weight=1)
        
    def browse_bgm(self):
        filename = filedialog.askopenfilename(
            title="Select Background Music",
            filetypes=[("Audio Files", "*.mp3 *.wav *.m4a"), ("All Files", "*.*")]
        )
        if filename:
            self.layer3_bgm_path.delete(0, tk.END)
            self.layer3_bgm_path.insert(0, filename)
            
    def collect_config(self):
        """Collect all values from UI"""
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
                "font_bold": 'selected' in self.layer3_font_bold.state(),
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
        
    def save_config(self):
        try:
            config = self.collect_config()
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            self.log("✅ Configuration saved successfully!")
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            self.log(f"❌ Error saving config: {e}")
            messagebox.showerror("Error", f"Failed to save config: {e}")
            
    def load_config_silent(self):
        """Load config without logging (called before UI is created)"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.merge_configs(loaded_config)
        except Exception as e:
            pass  # Silently use defaults
    
    def merge_configs(self, loaded_config):
        """Merge loaded config with defaults to ensure all keys exist"""
        for layer in self.config:
            if layer in loaded_config:
                for key in self.config[layer]:
                    if key in loaded_config[layer]:
                        self.config[layer][key] = loaded_config[layer][key]
            
    def load_config(self):
        """Load config with logging (called after UI is created)"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.merge_configs(loaded_config)
                self.log("✅ Configuration loaded successfully!")
        except Exception as e:
            self.log(f"⚠️ Using default configuration: {e}")
            
    def load_config_dialog(self):
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.config = json.load(f)
                self.log(f"✅ Configuration loaded from {filename}")
                messagebox.showinfo("Success", "Configuration loaded! Please restart to apply.")
            except Exception as e:
                self.log(f"❌ Error loading config: {e}")
                messagebox.showerror("Error", f"Failed to load config: {e}")
                
    def reset_config(self):
        if messagebox.askyesno("Reset Configuration", 
                               "Are you sure you want to reset all settings to default?"):
            # Reset to defaults and restart app
            self.root.destroy()
            root = tk.Tk()
            app = ShortsAutomationGUI(root)
            root.mainloop()
            
    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.update()
    
    def start_download(self):
        """Start YouTube download based on selected mode"""
        url = self.youtube_url.get().strip()
        mode = self.download_mode.get()
        
        if not url or url == "https://www.youtube.com/watch?v=...":
            messagebox.showerror("Error", "Please enter a valid YouTube URL!")
            return
        
        self.log(f"\n{'='*60}")
        self.log(f"📥 Starting Download...")
        self.log(f"Mode: {mode}")
        self.log(f"URL: {url}")
        self.log(f"{'='*60}\n")
        
        def run():
            try:
                if mode == "full":
                    # Full video download
                    cmd = [
                        "python", "downloader.py",
                        url
                    ]
                elif mode == "segment":
                    # Segment download
                    start = self.start_time.get().strip()
                    end = self.end_time.get().strip()
                    
                    if not start:
                        self.log("❌ Please enter a start time!")
                        return
                    
                    cmd = ["python", "downloader.py", url, start]
                    if end:
                        cmd.append(end)
                        
                elif mode == "live":
                    # Live stream download
                    duration = self.live_duration.get().strip()
                    cmd = ["python", "downloader.py", url, "--live"]
                    if duration:
                        cmd.append(duration)
                
                # Run download
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                for line in process.stdout:
                    self.log(line.rstrip())
                    
                process.wait()
                
                if process.returncode == 0:
                    self.log(f"\n✅ Download completed successfully!")
                    self.log(f"📁 Saved to downloads/ folder")
                    self.log(f"📋 Copied to vod.mp4 for processing")
                    messagebox.showinfo("Success", "Video downloaded!\n\nSaved to: downloads/\nCopied to: vod.mp4")
                else:
                    self.log(f"\n❌ Download failed!")
                    
            except Exception as e:
                self.log(f"\n❌ Error: {e}")
                messagebox.showerror("Error", f"Download failed: {e}")
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
    def run_layer(self, layer_num):
        self.save_config()
        self.log(f"\n{'='*60}")
        self.log(f"🚀 Starting Layer {layer_num}...")
        self.log(f"{'='*60}\n")
        
        def run():
            try:
                script_name = f"layer{layer_num}.py"
                process = subprocess.Popen(
                    ["python", script_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                for line in process.stdout:
                    self.log(line.rstrip())
                    
                process.wait()
                
                if process.returncode == 0:
                    self.log(f"\n✅ Layer {layer_num} completed successfully!")
                else:
                    self.log(f"\n❌ Layer {layer_num} failed with return code {process.returncode}")
                    
            except Exception as e:
                self.log(f"\n❌ Error running Layer {layer_num}: {e}")
                
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
    def run_all_layers(self):
        self.save_config()
        self.log(f"\n{'='*60}")
        self.log("⚡ Starting ALL LAYERS...")
        self.log(f"{'='*60}\n")
        
        def run():
            for layer in [1, 2, 3]:
                try:
                    self.log(f"\n🚀 Running Layer {layer}...\n")
                    script_name = f"layer{layer}.py"
                    process = subprocess.Popen(
                        ["python", script_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    
                    for line in process.stdout:
                        self.log(line.rstrip())
                        
                    process.wait()
                    
                    if process.returncode != 0:
                        self.log(f"\n❌ Layer {layer} failed! Stopping execution.")
                        return
                        
                except Exception as e:
                    self.log(f"\n❌ Error in Layer {layer}: {e}")
                    return
                    
            self.log(f"\n{'='*60}")
            self.log("✅ ALL LAYERS COMPLETED SUCCESSFULLY!")
            self.log(f"{'='*60}\n")
            
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ShortsAutomationGUI(root)
    root.mainloop()