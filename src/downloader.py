import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import re
import json
from datetime import datetime

class SubtitleDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Subtitle Downloader")
        self.geometry("1000x1000")
        
        self.mainframe = ttk.Frame(self, padding="20 20 20 20")
        self.mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        ttk.Label(self.mainframe, text="YouTube Channel URL or Playlist URL:").grid(
            column=0, row=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(self.mainframe, width=50)
        self.url_entry.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(self.mainframe, text="Download Subtitles", 
                  command=self.download_subtitles).grid(column=0, row=3, sticky=tk.W, pady=(10, 0))
        
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).grid(
            column=0, row=4, sticky=tk.W, pady=(10, 0))
    
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
            messagebox.showwarning("Error", 
                                 f"Could not update metadata file: {str(e)}")
    
    def download_subtitles(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube channel or playlist URL!")
            return
        
        identifier = self.extract_identifier_from_url(url)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_dir = os.path.join(project_root, "data", "input", identifier)
        vtt_dir = os.path.join(base_dir, "vtt_files")
        os.makedirs(vtt_dir, exist_ok=True)
        
        output_template = os.path.join(vtt_dir, "%(title)s [%(id)s].%(ext)s")
        total_downloaded = 0

        try:
            command = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--convert-subs", "vtt",
                "--print-json",
                "--download-archive", os.path.join(base_dir, "archive.txt"),
                "--retries", "3",  
                #"--sleep-subtitles", "1",  
                "--no-warnings",
                "--force-write-archive",
                "--no-overwrites", 
                "-o", output_template,
                url
            ]
            
            self.status_var.set("Starting download... (reruns will be required for playlists with more than 300 videos)")
            self.update()  
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while True:
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
                    vtt_path = os.path.join(vtt_dir, vtt_filename)
                    
                    new_entry = {
                        'id': video_id,
                        'title': video_title,
                        'vtt_path': vtt_path,
                        'url': video_data.get('webpage_url', ''),
                        'upload_date': video_data.get('upload_date', ''),
                        'duration': video_data.get('duration', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.update_metadata_file(base_dir, new_entry)
                    total_downloaded += 1
                    
                    if total_downloaded % 10 == 0:
                        self.status_var.set(f"Downloaded {total_downloaded} subtitles so far...")
                        self.update()
                        
                except json.JSONDecodeError:
                    continue
            
            json_file = os.path.join(base_dir, "metadata.json")
            if total_downloaded > 0:
                self.status_var.set(f"Downloaded {total_downloaded} subtitles to {identifier} folder!")
                messagebox.showinfo("Success", 
                    f"Successfully downloaded {total_downloaded} subtitle files.\n"
                    f"Metadata saved to:\n{json_file}")
            else:
                error = process.stderr.read()
                self.status_var.set(f"No subtitles downloaded. Error: {error[:200]}...")
                messagebox.showinfo("Info", f"No subtitles were downloaded. Error: {error[:500]}...")
                
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")

if __name__ == "__main__":
    app = SubtitleDownloader()
    app.mainloop()

# python3 src/downloader.py
