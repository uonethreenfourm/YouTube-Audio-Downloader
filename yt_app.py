#!/usr/bin/env python3
import subprocess
import re
import time
from pathlib import Path
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
from datetime import datetime
from queue import Queue
import hashlib
import sys
import os

OUTPUT_DIR = Path.home() / "Downloads" / "YouTube_Audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Optimized regex patterns (compiled for speed)
YT_PATTERNS = [
    re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([\w-]{11})'),
    re.compile(r'(?:https?://)?(?:www\.)?youtu\.be/([\w-]{11})'),
    re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([\w-]+)')
]

def find_yt_dlp():
    """Find yt-dlp executable - check bundled first, then system"""
    # Check if bundled with PyInstaller
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
        bundled = base_path / "yt-dlp.exe"
        if bundled.exists():
            return str(bundled)
    
    # Check system PATH
    try:
        result = subprocess.run(['where', 'yt-dlp'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'yt-dlp'
    except:
        pass
    
    return None

class YTDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Auto-Downloader")
        self.root.geometry("750x550")
        self.root.configure(bg="#2b2b2b")
        
        self.running = False
        self.done_urls = set()
        self.output_dir = OUTPUT_DIR
        self.download_queue = Queue()
        self.last_clip = ""
        self.download_count = 0
        self.yt_dlp_path = find_yt_dlp()
        
        # Header
        tk.Label(root, text=">> YouTube Audio Auto-Downloader", 
                font=("Arial", 14, "bold"), bg="#2b2b2b", fg="#00ff00").pack(pady=10)
        
        # Credits
        tk.Label(root, text="Made by ULENAM & SONAPSY-TEAM | Portable Edition", 
                font=("Arial", 8), bg="#2b2b2b", fg="#666666").pack()
        
        # Stats frame
        stats_frame = tk.Frame(root, bg="#2b2b2b")
        stats_frame.pack(pady=5)
        
        # Status
        self.status = tk.Label(stats_frame, text="Status: Ready", 
                              font=("Arial", 10, "bold"), bg="#2b2b2b", fg="#00ff00")
        self.status.pack(side=tk.LEFT, padx=10)
        
        # Download counter
        self.counter = tk.Label(stats_frame, text="Downloads: 0", 
                               font=("Arial", 10), bg="#2b2b2b", fg="#00aaff")
        self.counter.pack(side=tk.LEFT, padx=10)
        
        # Queue status
        self.queue_label = tk.Label(stats_frame, text="Queue: 0", 
                                    font=("Arial", 10), bg="#2b2b2b", fg="#ffaa00")
        self.queue_label.pack(side=tk.LEFT, padx=10)
        
        # Output
        self.folder_label = tk.Label(root, text=f"Output: {self.output_dir}", 
                               font=("Arial", 8), bg="#2b2b2b", fg="#888888", wraplength=650)
        self.folder_label.pack()
        
        # Change path
        tk.Button(root, text="Change Output Folder", command=self.change_path,
                 bg="#0066cc", fg="white", font=("Arial", 9), padx=10, pady=3).pack(pady=5)
        
        # Log
        log_frame = tk.Frame(root, bg="#2b2b2b")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_box = scrolledtext.ScrolledText(log_frame, height=18, width=85,
                                                 bg="#1e1e1e", fg="#00ff00",
                                                 font=("Courier", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.config(state=tk.DISABLED)
        
        # Buttons
        btn_frame = tk.Frame(root, bg="#2b2b2b")
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(btn_frame, text=">> START", command=self.start,
                                   bg="#00aa00", fg="white", font=("Arial", 11, "bold"),
                                   padx=25, pady=6)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="STOP", command=self.stop,
                                  bg="#aa0000", fg="white", font=("Arial", 11, "bold"),
                                  padx=25, pady=6, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Clear Log", command=self.clear_log,
                 bg="#555555", fg="white", font=("Arial", 9), padx=15, pady=6).pack(side=tk.LEFT, padx=5)
        
        # Check yt-dlp
        if not self.yt_dlp_path:
            self.log("[!] WARNING: yt-dlp not found!")
            self.log("[!] Install it with: pip install yt-dlp")
            messagebox.showerror("Missing Dependency", 
                "yt-dlp is not installed.\n\nRun: pip install yt-dlp")
        else:
            self.log("[+] yt-dlp found: Ready!")
        
        self.log("[*] PORTABLE EDITION - All bundled!")
        self.log("[*] Ready! Copy YouTube links to download audio automatically.")
    
    def log(self, msg):
        self.log_box.config(state=tk.NORMAL)
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{time_str}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete(1.0, tk.END)
        self.log_box.config(state=tk.DISABLED)
        self.log("Log cleared.")
    
    def change_path(self):
        folder = filedialog.askdirectory(title="Select Output Folder", 
                                        initialdir=str(self.output_dir))
        if folder:
            self.output_dir = Path(folder)
            self.folder_label.config(text=f"Output: {self.output_dir}")
            self.log(f"[+] Output folder changed: {self.output_dir}")
    
    def get_url(self, text):
        """Extract YouTube URL from text (optimized)"""
        for pattern in YT_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None
    
    def url_hash(self, url):
        """Create unique hash for URL tracking"""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def download_worker(self):
        """Background worker that processes download queue"""
        while self.running:
            try:
                if not self.download_queue.empty():
                    url = self.download_queue.get()
                    self.download(url)
                    self.download_queue.task_done()
                else:
                    time.sleep(0.3)
            except Exception as e:
                self.log(f"[-] Worker error: {str(e)[:60]}")
                time.sleep(1)
    
    def download(self, url):
        try:
            if not self.yt_dlp_path:
                self.log(f"[-] yt-dlp not available")
                return
            
            url_id = self.url_hash(url)
            self.log(f"[>] Downloading [{url_id}]: {url[:50]}...")
            
            cmd = [
                self.yt_dlp_path,
                '-x',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '-f', 'bestaudio',
                '--no-playlist',
                '--no-warnings',
                '--progress',
                '--newline',
                '-o', str(self.output_dir / '%(title)s.%(ext)s'),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                self.download_count += 1
                self.counter.config(text=f"Downloads: {self.download_count}")
                self.log(f"[+] Success! [{url_id}] Downloaded")
            else:
                err = result.stderr.split('\n')[0][:70] if result.stderr else "Unknown error"
                self.log(f"[-] [{url_id}] {err}")
        
        except subprocess.TimeoutExpired:
            self.log(f"[-] [{url_id}] Timeout (>10min)")
        except Exception as e:
            self.log(f"[-] [{url_id}] Error: {str(e)[:70]}")
        finally:
            self.queue_label.config(text=f"Queue: {self.download_queue.qsize()}")
    
    def monitor(self):
        """Optimized clipboard monitor"""
        import pyperclip
        
        self.log("[*] Monitor started with FAST mode (0.5s check interval)")
        
        while self.running:
            try:
                clip = pyperclip.paste()
                
                if clip and clip != self.last_clip:
                    self.last_clip = clip
                    
                    url = self.get_url(clip)
                    if url and url not in self.done_urls:
                        self.done_urls.add(url)
                        self.download_queue.put(url)
                        url_id = self.url_hash(url)
                        self.log(f"[+] Added to queue [{url_id}]: {url[:50]}...")
                        self.queue_label.config(text=f"Queue: {self.download_queue.qsize()}")
                
                time.sleep(0.5)
                
            except Exception as e:
                self.log(f"[!] Monitor error: {str(e)[:60]}")
                time.sleep(2)
        
        self.status.config(text="Status: Stopped", fg="#ff0000")
    
    def start(self):
        if not self.yt_dlp_path:
            messagebox.showerror("Error", "yt-dlp is required to run this app.")
            return
        
        if not self.running:
            self.running = True
            self.status.config(text="Status: [*] Monitoring...", fg="#00ff00")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.log("="*60)
            
            threading.Thread(target=self.monitor, daemon=True).start()
            
            for i in range(2):
                threading.Thread(target=self.download_worker, daemon=True).start()
            
            self.log("[+] 2 download workers started for parallel processing!")
    
    def stop(self):
        if self.running:
            self.running = False
            self.status.config(text="Status: Stopping...", fg="#ffaa00")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.log("[*] Stopping... (finishing current downloads)")
            
            def wait_and_stop():
                self.download_queue.join()
                self.status.config(text="Status: Stopped", fg="#ff0000")
                self.start_btn.config(state=tk.NORMAL)
                self.log("[+] All downloads finished. Stopped.")
            
            threading.Thread(target=wait_and_stop, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = YTDownloader(root)
    root.mainloop()
