# Intellicut Go 🎬⚡

An automated, multi-threaded video repurposing engine that transforms long-form media into short-form clips (TikTok/Reels/Shorts) using local AI transcription and dynamic FFmpeg rendering.

> **[Insert a GIF here showing the UI and the Progress Bar moving]**

## 🚀 The Problem
Editing short-form content with dynamic captions, background music, and branding takes hours in Premiere Pro. Intellicut Go automates this entire pipeline locally, removing the need for cloud subscriptions or manual timeline slicing.

## ⚙️ Core Architecture
* **The Engine:** A Python-driven integration of `subprocess` to manage complex `ffmpeg` audio/video filter chains asynchronously.
* **Local AI Inference:** Utilizes `OpenAI Whisper` and `PyTorch` for automated, timestamped karaoke-style subtitles.
* **Multithreaded GUI:** Built with `CustomTkinter`, separating the heavy CPU/GPU rendering workloads from the main UI thread to prevent blocking.

## 🛠️ Features
- **Smart Formatting:** Auto-crops 16:9 to 9:16 with dynamic background blurring.
- **AI Captions:** Word-level karaoke subtitles generated completely offline.
- **Automated Mixing:** Mixes background audio tracks and burns in persistent watermark branding.

## 💻 Installation & Usage
1. Ensure [FFmpeg](https://ffmpeg.org/download.html) is installed on your system.
2. Clone this repository:
   ```bash
   git clone [https://github.com/yourusername/intellicut-go.git](https://github.com/yourusername/intellicut-go.git)

## 📄 License
Distributed under the MIT License. 

Install dependencies: pip install -r requirements.txt

Run the engine: python main.py