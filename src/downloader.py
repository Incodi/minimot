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
    
    def validate_date(self, date_str):
        """Validate the date format (YYYYMMDD)"""
        if not date_str:
            return True
        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False
    
    def extract_identifier_from_url(self, url):
        """Extract channel handle or playlist ID from URL"""
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
    
    def create_metadata_file(self, base_dir, metadata):
        try:
            json_file = os.path.join(base_dir, "metadata.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not create metadata file: {str(e)}")
    
    def download_subtitles(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube channel or playlist URL")
            return
        
        date_after = self.date_after_entry.get().strip()
        date_before = self.date_before_entry.get().strip()
        
        if date_after and not self.validate_date(date_after):
            messagebox.showerror("Error", "Invalid 'After Date' format. Please use YYYYMMDD.")
            return
        
        if date_before and not self.validate_date(date_before):
            messagebox.showerror("Error", "Invalid 'Before Date' format. Please use YYYYMMDD.")
            return
        
        identifier = self.extract_identifier_from_url(url)

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_dir = os.path.join(project_root, "data", "input", identifier)
        
        vtt_dir = os.path.join(base_dir, "vtt_files")
        os.makedirs(vtt_dir, exist_ok=True)
        
        output_template = os.path.join(vtt_dir, "%(title)s [%(id)s].%(ext)s")
        metadata = []
    
        try:
            command = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--convert-subs", "vtt",
                "--print-json",
                "--download-archive", os.path.join(base_dir, "archive.txt"),
                "-o", output_template,
                url
            ]
            
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            for line in result.stdout.splitlines():
                try:
                    video_data = json.loads(line)
                    if '_type' in video_data and video_data['_type'] == 'playlist':
                        continue 
                    
                    video_id = video_data.get('id', '')
                    video_title = video_data.get('title', '')
                    vtt_filename = f"{video_title} [{video_id}].en.vtt"
                    vtt_path = os.path.join(vtt_dir, vtt_filename)
                    
                    metadata.append({
                        'id': video_id,
                        'title': video_title,
                        'vtt_path': vtt_path,
                        'url': video_data.get('webpage_url', ''),
                        'upload_date': video_data.get('upload_date', ''),
                        'duration': video_data.get('duration', '')
                    })
                except json.JSONDecodeError:
                    continue
            
            if metadata:
                self.create_metadata_file(base_dir, metadata)
                self.status_var.set(f"Downloaded {len(metadata)} subtitles to {identifier} folder!")
                messagebox.showinfo("Success", 
                    f"Successfully downloaded {len(metadata)} subtitle files.\n"
                    f"Metadata saved to:\n{os.path.join(base_dir, 'metadata.txt')}")
            else:
                self.status_var.set("No subtitles were downloaded (no matching videos?)")
                messagebox.showinfo("Info", "No subtitles were downloaded. Check your date filters or URL.")
                
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to download subtitles. Make sure yt-dlp is installed.\nError: {e.stderr}")
            self.status_var.set("Error downloading subtitles")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.status_var.set("Error downloading subtitles")

if __name__ == "__main__":
    app = SubtitleDownloader()
    app.mainloop()
