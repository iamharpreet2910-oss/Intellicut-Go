import os
import subprocess
import json
import shutil
import sys

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
        """Robust check for FFmpeg in PATH or local directory (Cross-Platform)"""
        # 1. Check System PATH
        if shutil.which("ffmpeg"):
            self.log(">> [SYSTEM] Found FFmpeg in System PATH.")
            return True
        
        # 2. Check Local Folder (handles Windows .exe and Mac/Linux binaries)
        ext = ".exe" if sys.platform == "win32" else ""
        local_ffmpeg = os.path.join(os.getcwd(), f"ffmpeg{ext}")
        local_ffprobe = os.path.join(os.getcwd(), f"ffprobe{ext}")
        
        if os.path.exists(local_ffmpeg):
            self.log(">> [SYSTEM] Found FFmpeg in local folder.")
            self.ffmpeg_cmd = local_ffmpeg
            if os.path.exists(local_ffprobe):
                self.ffprobe_cmd = local_ffprobe
            return True
            
        # 3. Fail
        self.log(">> [CRITICAL] FFmpeg missing! Please install it or place ffmpeg binary here.")
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
            si = None
            if sys.platform == "win32":
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
        
        si = None
        if sys.platform == "win32":
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
                '-t', str(part_dur),
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '192k', '-y', final_out
            ]

            self.log(f"   > Rendering FX & Exporting...")
            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=True, startupinfo=si, encoding='utf-8', errors='replace'
                )
                
                for line in process.stdout: 
                    if "Error" in line: self.log(f"[FFMPEG] {line.strip()}")
                
                process.wait()

                if process.returncode == 0:
                    self.log(f"   > [SUCCESS] Saved: {os.path.basename(final_out)}")
                else:
                    self.log(f"   > [ERROR] FFmpeg returned error code {process.returncode}")

            except Exception as e:
                self.log(f"   > [ERROR] Render failed: {e}")

            # Proper Error Logging Cleanup
            if os.path.exists(temp_audio):
                try: os.remove(temp_audio)
                except OSError as e: self.log(f"   > [WARN] Cleanup failed for audio: {e}")
            if srt_file and os.path.exists(srt_file): 
                try: os.remove(srt_file)
                except OSError as e: self.log(f"   > [WARN] Cleanup failed for subs: {e}")

        self.update_progress(1.0)
        self.log("\n--- BATCH COMPLETE ---")