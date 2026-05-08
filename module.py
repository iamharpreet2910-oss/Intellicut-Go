import customtkinter as ctk
import threading
import time
import os
import subprocess
import json
import random
import shutil
from tkinter import filedialog, messagebox

# --- 1. VISUAL IDENTITY & THEME ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") 

# Professional Color Palette (Matte Black & Cyber-Cyan)
COL_BG = "#121212"        # Main Background
COL_SIDEBAR = "#1E1E1E"   # Sidebar Background
COL_PANEL = "#252525"     # Content Panels
COL_ACCENT = "#00B4D8"    # Primary Action (Cyan)
COL_HOVER = "#0096C7"     # Button Hover
COL_TEXT_MAIN = "#FFFFFF" # Readable White
COL_TEXT_SUB = "#A0A0A0"  # Subtle Grey
COL_SUCCESS = "#00FF41"   # Matrix Green for success

# --- 2. INTELLICUT ENGINE (PRODUCTION READY) ---
class IntellicutEngine:
    def __init__(self, log_func, progress_func):
        self.log = log_func
        self.update_progress = progress_func
        self.model = None 
        self.model_loaded = False
        
        # Default command (will be updated by find_ffmpeg)
        self.ffmpeg_cmd = "ffmpeg"
        self.ffprobe_cmd = "ffprobe"
        
        # Default Audio Levels
        self.VOL_GAME = "0.8"
        self.VOL_VOICE = "1.5"
        
        # Check components
        self.has_ffmpeg = self.find_ffmpeg()
        self.can_transcribe = False
        self.check_whisper()

    def find_ffmpeg(self):
        """Robust check for FFmpeg in PATH or local directory"""
        # 1. Check System PATH
        if shutil.which("ffmpeg"):
            self.log(">> [SYSTEM] Found FFmpeg in System PATH.")
            return True
        
        # 2. Check Local Folder
        local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
        local_ffprobe = os.path.join(os.getcwd(), "ffprobe.exe")
        
        if os.path.exists(local_ffmpeg):
            self.log(">> [SYSTEM] Found FFmpeg in local folder.")
            self.ffmpeg_cmd = local_ffmpeg
            if os.path.exists(local_ffprobe):
                self.ffprobe_cmd = local_ffprobe
            return True
            
        # 3. Fail
        self.log(">> [CRITICAL] FFmpeg missing! Please install it or place ffmpeg.exe here.")
        return False

    def check_whisper(self):
        try:
            import whisper
            import torch
            self.can_transcribe = True
        except ImportError:
            self.can_transcribe = False
            self.log(">> [WARN] Whisper/Torch missing. AI Subtitles disabled.")

    def load_whisper_model(self):
        if self.model_loaded: return
        import whisper
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.log(f">> [SYSTEM] Loading AI Model on {device.upper()}... (One-time load)")
        self.model = whisper.load_model("base", device=device)
        self.model_loaded = True

    def safe_path(self, path):
        # Escape paths for FFmpeg filters (Windows compat)
        return os.path.abspath(path).replace("\\", "/").replace(":", "\\:")

    def get_video_info(self, file_path):
        cmd = [self.ffprobe_cmd, '-v', 'error', '-show_entries', 'format=duration:stream=width,height', '-of', 'json', file_path]
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=si)
            data = json.loads(result.stdout)
            dur = float(data['format']['duration'])
            w = next((int(s['width']) for s in data.get('streams', []) if 'width' in s), 0)
            h = next((int(s['height']) for s in data.get('streams', []) if 'height' in s), 0)
            return dur, w, h
        except Exception as e:
            self.log(f">> [ERROR] File Analysis Failed: {e}")
            return None, 0, 0

    def generate_karaoke_subs(self, audio_path):
        if not self.can_transcribe: return None
        self.load_whisper_model()
        
        try:
            result = self.model.transcribe(audio_path, word_timestamps=True, fp16=False)
            srt_path = audio_path.replace(".wav", ".srt")
            
            def fmt_time(s):
                m, s = divmod(s, 60)
                h, m = divmod(m, 60)
                ms = int((s % 1) * 1000)
                return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"

            with open(srt_path, "w", encoding="utf-8") as f:
                idx = 1
                for segment in result["segments"]:
                    words = segment.get("words", [])
                    if not words: continue
                    for i, word_obj in enumerate(words):
                        start = fmt_time(word_obj["start"])
                        end = fmt_time(word_obj["end"])
                        colored = []
                        for j, w in enumerate(words):
                            clean = w["word"].strip().upper()
                            if j == i: colored.append(f'<font color="#FFFF00">{clean}</font>')
                            else: colored.append(f'<font color="#FFFFFF">{clean}</font>')
                        f.write(f"{idx}\n{start} --> {end}\n{' '.join(colored)}\n\n")
                        idx += 1
            return srt_path
        except Exception as e:
            self.log(f">> [ERROR] AI Gen Failed: {e}")
            return None

    def run_process(self, input_file, parts, aspect_ratio, custom_logo, custom_music, use_subs, sub_style, use_blur, use_prog):
        if not self.has_ffmpeg:
            self.log(">> [STOPPED] FFmpeg is missing. Cannot proceed.")
            return
        if not input_file: return
        
        # Setup Dirs
        cwd = os.getcwd()
        dirs = {k: os.path.join(cwd, v) for k, v in [
            ('out', 'Output_Intellicut'), ('temp', 'Temp_Data')
        ]}
        for d in dirs.values(): os.makedirs(d, exist_ok=True)
        
        fname = os.path.basename(input_file)
        base_name = os.path.splitext(fname)[0]
        
        # 1. Analyze
        total_dur, w, h = self.get_video_info(input_file)
        if not total_dur: return

        part_dur = total_dur / parts
        self.log(f"--- PROCESSING {parts} CLIPS ({part_dur:.1f}s each) ---")
        
        # Target Res Logic
        target_w, target_h = w, h
        if aspect_ratio == "9:16 (TikTok)": target_w, target_h = int(h * (9/16)), h
        elif aspect_ratio == "1:1 (Square)": target_w, target_h = h, h
        
        if target_w % 2 != 0: target_w -= 1
        if target_h % 2 != 0: target_h -= 1
        
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # === SLICE-FIRST LOOP ===
        for i in range(parts):
            start_time = i * part_dur
            clip_num = i + 1
            
            self.log(f"\n>> [CLIP {clip_num}/{parts}] Initializing...")
            self.update_progress((i / parts))

            temp_audio = os.path.join(dirs['temp'], f'temp_audio_{clip_num}.wav')
            final_out = os.path.join(dirs['out'], f"{base_name}_Part{clip_num}.mp4")

            # A. Extract Audio (Reset Timestamps)
            subprocess.run([
                self.ffmpeg_cmd, '-ss', str(start_time), '-t', str(part_dur), 
                '-i', input_file, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-y', temp_audio
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=si)

            # B. Subtitles
            srt_file = None
            if use_subs:
                self.log(f"   > AI Transcription...")
                srt_file = self.generate_karaoke_subs(temp_audio)

            # C. Render Command Construction
            cmd_inputs = []
            
            # Input 0: Video Slice
            cmd_inputs.extend(['-ss', str(start_time), '-t', str(part_dur), '-i', input_file])
            input_idx = 1
            
            # Branding Input (Selected by User)
            logo_idx = -1
            if custom_logo and os.path.exists(custom_logo):
                # FIX: -loop 1 ensures logo persists
                cmd_inputs.extend(['-loop', '1', '-i', custom_logo])
                logo_idx = input_idx
                input_idx += 1

            # Filter Chain
            vf = ""
            last_v = "[0:v]"
            
            # 1. Blur/Crop
            if use_blur:
                vf += f"{last_v}split[bg][fg];" \
                      f"[bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=20:10[blurred];" \
                      f"[fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[clean_fg];" \
                      f"[blurred][clean_fg]overlay=(W-w)/2:(H-h)/2[v_merged];"
                last_v = "[v_merged]"
            else:
                if target_w != w or target_h != h:
                    crop_x = max(0, min(int((w/2)-(target_w/2)), w-target_w))
                    vf += f"{last_v}crop={target_w}:{target_h}:{crop_x}:0[v_cropped];"
                    last_v = "[v_cropped]"
            
            # 2. Color Grade
            vf += f"{last_v}eq=gamma=1.05:saturation=1.2[v_color];"
            last_v = "[v_color]"

            # 3. Branding Overlay
            if logo_idx != -1:
                # FIX: shortest=1 stops the infinite logo loop
                vf += f"[{logo_idx}:v]scale=150:-1[logo];{last_v}[logo]overlay=30:30:shortest=1[v_branded];"
                last_v = "[v_branded]"
            
            # 4. Subs
            if srt_file:
                clean_srt = self.safe_path(srt_file)
                f_name = sub_style.get('font', 'Arial')
                f_size = sub_style.get('size', 16)
                style = (f"Fontname={f_name},Fontsize={f_size},PrimaryColour=&HFFFFFF&,"
                         f"BorderStyle=1,Outline=1,Shadow=0,MarginV=60,Alignment=2,Bold=1")
                vf += f"{last_v}subtitles='{clean_srt}':force_style='{style}'[v_subs];"
                last_v = "[v_subs]"
            
            # 5. Progress Bar
            if use_prog:
                # FIX: Use part_dur for calculation
                vf += f"color=c=red:s={target_w}x15[c_red];" \
                      f"[c_red]scale=eval=frame:w='max(1, (t/{part_dur})*{target_w})':h=15[pbar];" \
                      f"{last_v}[pbar]overlay=x=0:y=H-15[v_final];"
                last_v = "[v_final]"

            # Audio Mix
            af = f"[0:a]volume={self.VOL_GAME}[a_main];"
            mix_cnt = 1
            mix_inputs = "[a_main]"
            
            # Music Input (Selected by User)
            if custom_music and os.path.exists(custom_music):
                cmd_inputs.extend(['-i', custom_music])
                af += f"[{input_idx}:a]volume={self.VOL_VOICE}[a_music];"
                mix_inputs += "[a_music]"
                input_idx+=1; mix_cnt+=1

            vf += f"{af}{mix_inputs}amix=inputs={mix_cnt}:duration=first[a_out]"

            # Final Command
            cmd = [self.ffmpeg_cmd] + cmd_inputs + [
                '-filter_complex', vf, 
                '-map', last_v, '-map', '[a_out]',
                '-t', str(part_dur), # FIX: Hard stop to prevent infinite generation
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '192k', '-y', final_out
            ]

            self.log(f"   > Rendering FX & Exporting...")
            try:
                # Use Popen to stream output safely
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=True, startupinfo=si, encoding='utf-8', errors='replace'
                )
                
                # Consume output to keep buffer clear (optional logging here)
                for line in process.stdout: 
                    if "Error" in line: self.log(f"[FFMPEG] {line.strip()}")
                
                process.wait()

                if process.returncode == 0:
                    self.log(f"   > [SUCCESS] Saved: {os.path.basename(final_out)}")
                else:
                    self.log(f"   > [ERROR] FFmpeg returned error code {process.returncode}")

            except Exception as e:
                self.log(f"   > [ERROR] Render failed: {e}")

            # Cleanup
            try: os.remove(temp_audio)
            except: pass
            if srt_file: 
                try: os.remove(srt_file)
                except: pass

        self.update_progress(1.0)
        self.log("\n--- BATCH COMPLETE ---")

# --- 3. PROFESSIONAL UI (FIXED STARTUP & SELECTION) ---
class IntellicutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("INTELLICUT GO")
        self.geometry("1050x800")
        self.configure(fg_color=COL_BG)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Paths
        self.video_path = ""
        self.logo_path = ""
        self.music_path = ""
        
        # 1. SETUP UI FIRST (Crucial: Console must exist before Engine starts)
        self.setup_sidebar()
        self.setup_main_area()
        
        # 2. INITIALIZE ENGINE (Now safe to log messages)
        self.engine = IntellicutEngine(self.console_log, self.update_bar)
        
        self.console_log(">> SYSTEM READY.")
        self.console_log(">> ENGINE INITIALIZED.")

    def setup_sidebar(self):
        # Sidebar Container
        sb = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COL_SIDEBAR)
        sb.grid(row=0, column=0, sticky="nsew")
        
        # Branding Header
        header = ctk.CTkFrame(sb, fg_color="transparent")
        header.pack(pady=(35, 25))
        
        ctk.CTkLabel(header, text="INTELLICUT", font=("Montserrat", 34, "bold"), text_color="white").pack()
        ctk.CTkLabel(header, text="GO VERSION", font=("Code", 14, "bold"), text_color=COL_ACCENT).pack(pady=(2, 5))
        ctk.CTkLabel(header, text="powered by xevora", font=("Arial", 10, "italic"), text_color="#666").pack()
        
        # Divider
        ctk.CTkFrame(sb, height=2, fg_color="#333").pack(fill="x", padx=25, pady=10)

        # Config Section
        self.create_label(sb, "PROJECT CONFIGURATION")
        
        self.opt_ratio = ctk.CTkOptionMenu(
            sb, values=["9:16 (TikTok)", "1:1 (Square)", "16:9 (Youtube)"], 
            fg_color=COL_PANEL, button_color=COL_ACCENT, button_hover_color=COL_HOVER,
            text_color="white", dropdown_fg_color=COL_PANEL, dropdown_text_color="white"
        )
        self.opt_ratio.pack(fill="x", padx=25, pady=5)

        self.create_label(sb, "SLICE COUNT")
        self.lbl_parts = ctk.CTkLabel(sb, text="1 Clip", text_color=COL_ACCENT, font=("Roboto", 12, "bold"))
        self.lbl_parts.pack(anchor="e", padx=25)
        
        self.sld_parts = ctk.CTkSlider(
            sb, from_=1, to=20, number_of_steps=19, 
            progress_color=COL_ACCENT, button_color="white", 
            button_hover_color=COL_HOVER, command=self.update_parts_lbl
        )
        self.sld_parts.pack(fill="x", padx=25, pady=5)
        self.sld_parts.set(1)

        # Footer
        ctk.CTkLabel(sb, text="v13.0 Stable Build", font=("Consolas", 10), text_color="#444").pack(side="bottom", pady=20)

    def setup_main_area(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

        # 1. File Input Area
        input_panel = ctk.CTkFrame(main, fg_color=COL_PANEL, corner_radius=8, border_width=1, border_color="#333")
        input_panel.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(input_panel, text="SOURCE MEDIA", font=("Roboto", 11, "bold"), text_color=COL_TEXT_SUB).pack(anchor="w", padx=20, pady=(15,5))
        
        inner_input = ctk.CTkFrame(input_panel, fg_color="transparent")
        inner_input.pack(fill="x", padx=15, pady=(0,15))
        
        self.ent_path = ctk.CTkEntry(
            inner_input, placeholder_text="Path to video file...", 
            fg_color="#121212", border_color="#444", text_color="white", height=35
        )
        self.ent_path.pack(side="left", fill="x", expand=True, padx=(0,10))
        
        btn_browse = ctk.CTkButton(
            inner_input, text="SELECT FILE", width=120, height=35,
            fg_color=COL_ACCENT, text_color="black", font=("Roboto", 11, "bold"),
            hover_color=COL_HOVER, command=self.browse
        )
        btn_browse.pack(side="right")

        # 2. Tabs
        self.tabs = ctk.CTkTabview(
            main, fg_color=COL_PANEL, segmented_button_fg_color="#121212", 
            segmented_button_selected_color=COL_ACCENT, segmented_button_selected_hover_color=COL_HOVER,
            segmented_button_unselected_color="#121212", segmented_button_unselected_hover_color="#333",
            text_color="white"
        )
        self.tabs.pack(fill="both", expand=True, pady=(0, 20))
        
        self.tabs.add("DASHBOARD")
        self.tabs.add("FX STUDIO")
        self.tabs.add("CONSOLE")
        
        # --- TAB 1: DASHBOARD ---
        t1 = self.tabs.tab("DASHBOARD")
        
        # Branding
        self.sw_brand = self.create_switch(t1, "Apply Branding (Watermark)")
        self.sw_brand.select()
        self.btn_logo = ctk.CTkButton(t1, text="SELECT LOGO (.png)", height=32, 
                                      fg_color="#333", hover_color="#444", border_width=1, border_color="#555",
                                      command=self.browse_logo)
        self.btn_logo.pack(fill="x", padx=25, pady=(0, 20))

        # Audio
        self.sw_vo = self.create_switch(t1, "Mix Background Music")
        self.btn_music = ctk.CTkButton(t1, text="SELECT AUDIO (.mp3)", height=32, 
                                       fg_color="#333", hover_color="#444", border_width=1, border_color="#555",
                                       command=self.browse_music)
        self.btn_music.pack(fill="x", padx=25, pady=(0, 20))
        
        # Subs
        self.sw_subs = self.create_switch(t1, "AI Auto-Captions (Whisper)")
        self.sw_subs.select()

        # --- TAB 2: FX STUDIO ---
        t2 = self.tabs.tab("FX STUDIO")
        
        self.create_label(t2, "VISUAL PROCESSING")
        self.sw_blur = ctk.CTkSwitch(t2, text="Smart Background Blur (Fill)", progress_color=COL_ACCENT, text_color="white")
        self.sw_blur.pack(anchor="w", padx=25, pady=8); self.sw_blur.select()
        
        self.sw_prog = ctk.CTkSwitch(t2, text="Dynamic Red Progress Bar", progress_color=COL_ACCENT, text_color="white")
        self.sw_prog.pack(anchor="w", padx=25, pady=8); self.sw_prog.select()
        
        ctk.CTkFrame(t2, height=1, fg_color="#444").pack(fill="x", padx=25, pady=15)
        
        self.create_label(t2, "TYPOGRAPHY")
        self.opt_font = ctk.CTkOptionMenu(
            t2, values=["Arial", "Impact", "Verdana", "Tahoma"], 
            fg_color="#121212", button_color="#333", button_hover_color="#444", text_color="white"
        )
        self.opt_font.pack(fill="x", padx=25, pady=5)
        
        ctk.CTkLabel(t2, text="Font Size Scale", font=("Roboto", 11), text_color=COL_TEXT_SUB).pack(anchor="w", padx=25, pady=(15,5))
        self.sld_size = ctk.CTkSlider(t2, from_=10, to=80, progress_color=COL_ACCENT, button_color="white")
        self.sld_size.pack(fill="x", padx=25, pady=5); self.sld_size.set(24)

        # --- TAB 3: CONSOLE ---
        self.console = ctk.CTkTextbox(
            self.tabs.tab("CONSOLE"), font=("Consolas", 11), 
            text_color=COL_SUCCESS, fg_color="black", border_width=1, border_color="#333"
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=10)

        # 3. Action Bar
        action_bar = ctk.CTkFrame(main, fg_color="transparent")
        action_bar.pack(fill="x", side="bottom")
        
        self.progress_bar = ctk.CTkProgressBar(action_bar, progress_color=COL_ACCENT, height=10)
        self.progress_bar.pack(fill="x", pady=(0, 15))
        self.progress_bar.set(0)
        
        self.btn_run = ctk.CTkButton(
            action_bar, text="INITIATE RENDER SEQUENCE", height=55, 
            font=("Montserrat", 15, "bold"), fg_color=COL_ACCENT, text_color="black", 
            hover_color=COL_HOVER, command=self.start
        )
        self.btn_run.pack(fill="x")

    # --- HELPERS ---
    def create_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Roboto", 11, "bold"), text_color=COL_TEXT_SUB).pack(anchor="w", padx=25, pady=(20,5))

    def create_switch(self, parent, text):
        sw = ctk.CTkSwitch(parent, text=text, font=("Roboto", 12), progress_color=COL_ACCENT, text_color="white", button_color="white")
        sw.pack(anchor="w", pady=5, padx=5)
        return sw

    def update_parts_lbl(self, val):
        self.lbl_parts.configure(text=f"{int(val)} Clip(s)")

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv")])
        if f: 
            self.video_path = f
            self.ent_path.delete(0, "end"); self.ent_path.insert(0, f)
            self.console_log(f">> MEDIA LOADED: {os.path.basename(f)}")

    def browse_logo(self):
        f = filedialog.askopenfilename(filetypes=[("Image", "*.png")])
        if f:
            self.logo_path = f
            self.btn_logo.configure(text=f"LOGO: {os.path.basename(f)}", fg_color=COL_ACCENT, text_color="black")

    def browse_music(self):
        f = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav")])
        if f:
            self.music_path = f
            self.btn_music.configure(text=f"AUDIO: {os.path.basename(f)}", fg_color=COL_ACCENT, text_color="black")

    def console_log(self, msg):
        self.console.insert("end", msg + "\n"); self.console.see("end")

    def update_bar(self, val):
        self.progress_bar.set(val)

    def start(self):
        if not self.video_path: 
            messagebox.showwarning("Input Error", "Please select a source video file.")
            return

        self.btn_run.configure(state="disabled", text="PROCESSING... CHECK CONSOLE")
        self.tabs.set("CONSOLE")
        
        args = {
            'input_file': self.video_path,
            'parts': int(self.sld_parts.get()),
            'aspect_ratio': self.opt_ratio.get(),
            # Logic: Send path if switch is ON, else None
            'custom_logo': self.logo_path if self.sw_brand.get() else None,
            'custom_music': self.music_path if self.sw_vo.get() else None,
            'use_subs': self.sw_subs.get(),
            'use_blur': self.sw_blur.get(),
            'use_prog': self.sw_prog.get(),
            'sub_style': {'font': self.opt_font.get(), 'size': int(self.sld_size.get())}
        }
        
        threading.Thread(target=self.run_bg, args=(args,)).start()

    def run_bg(self, args):
        self.engine.run_process(**args)
        self.btn_run.configure(state="normal", text="INITIATE RENDER SEQUENCE")

if __name__ == "__main__":
    app = IntellicutApp()
    app.mainloop()