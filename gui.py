import customtkinter as ctk
import threading
import os
from tkinter import filedialog, messagebox
from engine import IntellicutEngine

# --- VISUAL IDENTITY & THEME ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") 

COL_BG = "#121212"        # Main Background
COL_SIDEBAR = "#1E1E1E"   # Sidebar Background
COL_PANEL = "#252525"     # Content Panels
COL_ACCENT = "#00B4D8"    # Primary Action (Cyan)
COL_HOVER = "#0096C7"     # Button Hover
COL_TEXT_MAIN = "#FFFFFF" # Readable White
COL_TEXT_SUB = "#A0A0A0"  # Subtle Grey
COL_SUCCESS = "#00FF41"   # Matrix Green for success

class IntellicutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("INTELLICUT GO")
        self.geometry("1050x800")
        self.configure(fg_color=COL_BG)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.video_path = ""
        self.logo_path = ""
        self.music_path = ""
        
        self.setup_sidebar()
        self.setup_main_area()
        
        self.engine = IntellicutEngine(self.console_log, self.update_bar)
        
        self.console_log(">> SYSTEM READY.")
        self.console_log(">> ENGINE INITIALIZED.")

    def setup_sidebar(self):
        sb = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COL_SIDEBAR)
        sb.grid(row=0, column=0, sticky="nsew")
        
        header = ctk.CTkFrame(sb, fg_color="transparent")
        header.pack(pady=(35, 25))
        
        ctk.CTkLabel(header, text="INTELLICUT", font=("Montserrat", 34, "bold"), text_color="white").pack()
        ctk.CTkLabel(header, text="GO VERSION", font=("Code", 14, "bold"), text_color=COL_ACCENT).pack(pady=(2, 5))
        ctk.CTkLabel(header, text="powered by xevora", font=("Arial", 10, "italic"), text_color="#666").pack()
        
        ctk.CTkFrame(sb, height=2, fg_color="#333").pack(fill="x", padx=25, pady=10)

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

        ctk.CTkLabel(sb, text="v13.0 Stable Build", font=("Consolas", 10), text_color="#444").pack(side="bottom", pady=20)

    def setup_main_area(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

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
        
        t1 = self.tabs.tab("DASHBOARD")
        self.sw_brand = self.create_switch(t1, "Apply Branding (Watermark)")
        self.sw_brand.select()
        self.btn_logo = ctk.CTkButton(t1, text="SELECT LOGO (.png)", height=32, 
                                      fg_color="#333", hover_color="#444", border_width=1, border_color="#555",
                                      command=self.browse_logo)
        self.btn_logo.pack(fill="x", padx=25, pady=(0, 20))

        self.sw_vo = self.create_switch(t1, "Mix Background Music")
        self.btn_music = ctk.CTkButton(t1, text="SELECT AUDIO (.mp3)", height=32, 
                                       fg_color="#333", hover_color="#444", border_width=1, border_color="#555",
                                       command=self.browse_music)
        self.btn_music.pack(fill="x", padx=25, pady=(0, 20))
        
        self.sw_subs = self.create_switch(t1, "AI Auto-Captions (Whisper)")
        self.sw_subs.select()

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

        self.console = ctk.CTkTextbox(
            self.tabs.tab("CONSOLE"), font=("Consolas", 11), 
            text_color=COL_SUCCESS, fg_color="black", border_width=1, border_color="#333"
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=10)

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