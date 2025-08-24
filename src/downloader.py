import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import re
import json
from datetime import datetime
import sys
import threading
import queue

class SubDownloader(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Subtitle Downloader")
        self.geometry("1000x600")
        
        self.mainframe = ttk.Frame(self, padding="20 20 20 20")
        self.mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        ttk.Label(self.mainframe, text="YouTube Channel URL or Playlist URL:").grid(
            column=0, row=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(self.mainframe, width=100)
        self.url_entry.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.download_button = ttk.Button(self.mainframe, text="Download Subtitles", 
                                       command=self.start_download_thread)
        self.download_button.grid(column=0, row=3, sticky=tk.W, pady=(10, 0))
        
        self.progress = ttk.Progressbar(self.mainframe, orient='horizontal', length=400, mode='determinate')
        self.progress.grid(column=0, row=4, sticky=tk.W, pady=(10, 0))
        
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).grid(
            column=0, row=5, sticky=tk.W, pady=(10, 0))
        
        self.text_output = tk.Text(self.mainframe, height=30, wrap=tk.WORD)
        self.text_output.grid(column=0, row=6, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        scrollbar = ttk.Scrollbar(self.mainframe, orient=tk.VERTICAL, command=self.text_output.yview)
        scrollbar.grid(column=1, row=6, sticky=(tk.N, tk.S))
        self.text_output['yscrollcommand'] = scrollbar.set
        
        self.download_limit = 500 # download limit
        self.total_downloaded = 0
        self.download_thread = None
        self.stop_event = threading.Event()
        self.message_queue = queue.Queue()
        
        # Start checking the message queue
        self.after(100, self.process_queue)
        
    def start_download_thread(self):
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Warning", "Download is already in progress!")
            return
            
        self.stop_event.clear()
        self.download_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.text_output.delete(1.0, tk.END)
        self.total_downloaded = 0
        
        self.download_thread = threading.Thread(
            target=self.download_subtitles_threaded,
            daemon=True
        )
        self.download_thread.start()
    
    def download_subtitles_threaded(self):
        url = self.url_entry.get().strip()
        if not url:
            self.message_queue.put(("error", "Please enter a YouTube channel or playlist URL!"))
            return
        
        try:
            identifier = self.extract_identifier_from_url(url)
            channel_name = self.get_channel_name_from_url(url)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(project_root, "data", "input", identifier)
            vtt_dir = os.path.join(base_dir, "vtt_files")
            os.makedirs(vtt_dir, exist_ok=True)
            
            output_template = os.path.join(vtt_dir, "%(title)s [%(id)s].%(ext)s")
            self.total_downloaded = 0

            command = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--convert-subs", "vtt",
                "--print-json",
                "--download-archive", os.path.join(base_dir, "archive.txt"),
                "--retries", "3",
                #"--cookies-from-browser", "firefox", # to get members only videos
                #"--extractor-args", "youtubetab:skip=authcheck",
                "--no-warnings",
                "--force-write-archive",
                "--no-overwrites",  
                "--sleep-subtitles", "1",
                "--extractor-args", "youtube:player-client=default,mweb;po_token=bgutil:http-1.2.2",
                "-o", output_template,
                "--max-downloads", str(self.download_limit),
                url
            ]
            
            self.message_queue.put(("status", f"Starting download... (Max of {self.download_limit} subtitles will be downloaded)"))
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while True:
                if self.stop_event.is_set():
                    process.terminate()
                    self.message_queue.put(("status", "Download stopped by user"))
                    break
                    
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                try:
                    video_data = json.loads(line)
                    if '_type' in video_data and video_data['_type'] == 'playlist':
                        continue
                    
                    video_id = video_data.get('id', '')
                    video_title = video_data.get('title', '')
                    vtt_filename = f"{video_title} [{video_id}].en.vtt"
                    
                    new_entry = {
                        'id': video_id,
                        'title': video_title,
                        'url': video_data.get('webpage_url', ''),
                        'upload_date': video_data.get('upload_date', ''),
                        'duration': video_data.get('duration', ''),
                        'timestamp': datetime.now().isoformat(),
                        'channel_name': channel_name or video_data.get('channel', ''),
                        'channel_id': video_data.get('channel_id', ''),
                        'channel_url': video_data.get('channel_url', '')
                    }
                    
                    self.update_metadata_file(base_dir, new_entry)
                    self.total_downloaded += 1
                    
                    progress = (self.total_downloaded / self.download_limit) * 100
                    self.message_queue.put(("progress", progress))
                    self.message_queue.put(("log", f"Downloaded: {video_title}"))
                    
                    if self.total_downloaded >= self.download_limit:
                        process.terminate()
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            if self.total_downloaded > 0:
                self.message_queue.put(("status", f"Downloaded {self.total_downloaded} subtitles to {identifier} folder!"))
                self.message_queue.put(("log", f"\nMetadata saved to: {os.path.join(base_dir, 'metadata.json')}"))
            else:
                error = process.stderr.read()
                self.message_queue.put(("error", f"No subtitles downloaded. Error: {error[:200]}..."))
                
        except Exception as e:
            self.message_queue.put(("error", f"An unexpected error occurred: {str(e)}"))
        finally:
            self.message_queue.put(("done", None))
    
    def process_queue(self):
        try:
            while True:
                msg_type, msg_content = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self.status_var.set(msg_content)
                elif msg_type == "progress":
                    self.progress['value'] = msg_content
                elif msg_type == "log":
                    self.text_output.insert(tk.END, msg_content + "\n")
                    self.text_output.see(tk.END)
                elif msg_type == "error":
                    messagebox.showerror("Error", msg_content)
                elif msg_type == "done":
                    self.download_button.config(state=tk.NORMAL)
                    break
                    
        except queue.Empty:
            pass
            
        self.after(100, self.process_queue)
    
    def stop_download(self):
        self.stop_event.set()
    
    def extract_identifier_from_url(self, url):
        channel_patterns = [
            r'youtube\.com/c/([^/]+)',
            r'youtube\.com/channel/([^/]+)',
            r'youtube\.com/@([^/]+)',
            r'youtube\.com/user/([^/]+)'
        ]
        
        playlist_pattern = r'[&?]list=([^&]+)'
        
        for pattern in channel_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        match = re.search(playlist_pattern, url)
        if match:
            return match.group(1)
        
        return "youtube_subtitles"
    
    def get_channel_name_from_url(self, url):
        channel_patterns = [
            r'youtube\.com/c/([^/]+)',
            r'youtube\.com/channel/([^/]+)',
            r'youtube\.com/@([^/]+)',
            r'youtube\.com/user/([^/]+)'
        ]
        
        for pattern in channel_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def update_metadata_file(self, base_dir, new_entry):
        json_file = os.path.join(base_dir, "metadata.json")
        
        try:
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                metadata = []
            
            existing_ids = {item['id'] for item in metadata}
            if new_entry['id'] not in existing_ids:
                metadata.append(new_entry)
                
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                    
        except Exception as e:
            self.message_queue.put(("error", f"Could not update metadata file: {str(e)}"))
    
    def shutdown(self):
        self.stop_download()
        self.destroy()

if __name__ == "__main__":
    class StandaloneApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.downloader = SubDownloader(self)
    
    app = StandaloneApp()
    app.mainloop()
