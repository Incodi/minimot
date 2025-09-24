import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import re
import json
from datetime import datetime
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
        
        # Add checkbox for metadata-only update
        self.metadata_only_var = tk.BooleanVar()
        self.metadata_only_checkbox = ttk.Checkbutton(
            self.mainframe, 
            text="Update metadata only (don't download new subtitles)", 
            variable=self.metadata_only_var
        )
        self.metadata_only_checkbox.grid(column=0, row=2, sticky=tk.W, pady=(5, 0))
        
        self.download_button = ttk.Button(self.mainframe, text="Download Subtitles", 
                                       command=self.start_download)
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
        
        self.after(100, self.process_queue)
        
    def start_download(self):
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Warning", "Download is already in progress!")
            return
            
        self.stop_event.clear()
        self.download_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.text_output.delete(1.0, tk.END)
        self.total_downloaded = 0
        
        # Update button text based on mode
        if self.metadata_only_var.get():
            self.download_button.config(text="Updating Metadata...")
        else:
            self.download_button.config(text="Downloading...")
        
        self.download_thread = threading.Thread(
            target=self.download_subtitles,
            daemon=True
        )
        self.download_thread.start()
    
    def download_subtitles(self):
        url = self.url_entry.get().strip()
        if not url:
            self.message_queue.put(("error", "Please enter a YouTube channel or playlist URL!"))
            return
        
        metadata_only = self.metadata_only_var.get()
        
        try:
            identifier = self.extract_identifier_from_url(url)
            channel_name = self.get_channel_name_from_url(url)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(project_root, "data", "input", identifier)
            
            # Check if this channel/playlist has been downloaded before
            if metadata_only:
                if not os.path.exists(base_dir) or not os.path.exists(os.path.join(base_dir, "metadata.json")):
                    self.message_queue.put(("error", f"No previous downloads found for this channel/playlist. Directory: {base_dir}"))
                    return
                
                # Load existing metadata to get video IDs
                existing_video_ids = self.get_existing_video_ids(base_dir)
                if not existing_video_ids:
                    self.message_queue.put(("error", "No existing videos found in metadata.json"))
                    return
                
                self.message_queue.put(("status", f"Updating metadata for {len(existing_video_ids)} existing videos..."))
                self.update_metadata_only(existing_video_ids, base_dir, channel_name)
                return
            
            # Normal subtitle download mode
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
                #"--retries", "3",
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
                    
                    # Extract view count and like count
                    view_count = video_data.get('view_count', 0)
                    like_count = video_data.get('like_count', 0)
                    
                    # Format numbers for display (optional - you can remove this if you want raw numbers)
                    view_count_formatted = self.format_count(view_count) if view_count else "N/A"
                    like_count_formatted = self.format_count(like_count) if like_count else "N/A"
                    
                    new_entry = {
                        'id': video_id,
                        'title': video_title,
                        'url': video_data.get('webpage_url', ''),
                        'upload_date': video_data.get('upload_date', ''),
                        'duration': video_data.get('duration', ''),
                        'view_count': view_count,
                        'view_count_formatted': view_count_formatted,
                        'like_count': like_count,
                        'like_count_formatted': like_count_formatted,
                        'dislike_count': video_data.get('dislike_count', 0),  # Often not available due to YouTube changes
                        'comment_count': video_data.get('comment_count', 0),
                        'timestamp': datetime.now().isoformat(),
                        'channel_name': channel_name or video_data.get('channel', ''),
                        'channel_id': video_data.get('channel_id', ''),
                        'channel_url': video_data.get('channel_url', ''),
                        'subscriber_count': video_data.get('channel_follower_count', 0)  # Channel subscriber count
                    }
                    
                    self.update_metadata_file(base_dir, new_entry)
                    self.total_downloaded += 1
                    
                    progress = (self.total_downloaded / self.download_limit) * 100
                    self.message_queue.put(("progress", progress))
                    
                    # Enhanced log message with view and like counts
                    log_message = f"Downloaded: {video_title}"
                    if view_count:
                        log_message += f" | Views: {view_count_formatted}"
                    if like_count:
                        log_message += f" | Likes: {like_count_formatted}"
                    
                    self.message_queue.put(("log", log_message))
                    
                    if self.total_downloaded >= self.download_limit:
                        process.terminate()
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            if self.total_downloaded > 0:
                self.message_queue.put(("status", f"Downloaded {self.total_downloaded} subtitles to {identifier} folder!"))
                self.message_queue.put(("log", f"\nMetadata saved to: {os.path.join(base_dir, 'metadata.json')}"))
                self.message_queue.put(("log", f"Metadata includes: title, URL, upload date, duration, view count, like count, comment count, and channel info"))
            else:
                error = process.stderr.read()
                self.message_queue.put(("error", f"No subtitles downloaded. Error: {error[:200]}..."))
                
        except Exception as e:
            self.message_queue.put(("error", f"An unexpected error occurred: {str(e)}"))
        finally:
            self.message_queue.put(("done", None))
    
    def format_count(self, count):
        """Format large numbers with K, M, B suffixes for better readability"""
        if count is None:
            return "N/A"
        
        count = int(count)
        if count >= 1_000_000_000:
            return f"{count / 1_000_000_000:.1f}B"
        elif count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        else:
            return str(count)
    
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
                    self.download_button.config(text="Download Subtitles")  # Reset button text
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
    
    def get_existing_video_ids(self, base_dir):
        """Get list of video IDs from existing metadata.json"""
        json_file = os.path.join(base_dir, "metadata.json")
        try:
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    return [item['id'] for item in metadata if 'id' in item]
            return []
        except Exception:
            return []
    
    def update_metadata_only(self, video_ids, base_dir, channel_name):
        """Update metadata for existing videos without downloading subtitles"""
        try:
            updated_count = 0
            total_videos = len(video_ids)
            
            # Process videos in batches to avoid overwhelming yt-dlp
            batch_size = 50
            for i in range(0, total_videos, batch_size):
                if self.stop_event.is_set():
                    break
                
                batch_ids = video_ids[i:i+batch_size]
                batch_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in batch_ids]
                
                # Create yt-dlp command for metadata extraction only
                command = [
                    "yt-dlp",
                    "--skip-download",
                    "--print-json",
                    #"--retries", "3",
                    "--no-warnings",
                    "--extractor-args", "youtube:player-client=default,mweb;po_token=bgutil:http-1.2.2"
                ] + batch_urls
                
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                while True:
                    if self.stop_event.is_set():
                        process.terminate()
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
                        
                        # Extract updated metrics
                        view_count = video_data.get('view_count', 0)
                        like_count = video_data.get('like_count', 0)
                        view_count_formatted = self.format_count(view_count) if view_count else "N/A"
                        like_count_formatted = self.format_count(like_count) if like_count else "N/A"
                        
                        updated_entry = {
                            'id': video_id,
                            'title': video_title,
                            'url': video_data.get('webpage_url', ''),
                            'upload_date': video_data.get('upload_date', ''),
                            'duration': video_data.get('duration', ''),
                            'view_count': view_count,
                            'view_count_formatted': view_count_formatted,
                            'like_count': like_count,
                            'like_count_formatted': like_count_formatted,
                            'dislike_count': video_data.get('dislike_count', 0),
                            'comment_count': video_data.get('comment_count', 0),
                            'timestamp': datetime.now().isoformat(),
                            'channel_name': channel_name or video_data.get('channel', ''),
                            'channel_id': video_data.get('channel_id', ''),
                            'channel_url': video_data.get('channel_url', ''),
                            'subscriber_count': video_data.get('channel_follower_count', 0)
                        }
                        
                        self.update_existing_metadata(base_dir, updated_entry)
                        updated_count += 1
                        
                        # Update progress
                        progress = (updated_count / total_videos) * 100
                        self.message_queue.put(("progress", progress))
                        
                        # Log update
                        log_message = f"Updated: {video_title}"
                        if view_count:
                            log_message += f" | Views: {view_count_formatted}"
                        if like_count:
                            log_message += f" | Likes: {like_count_formatted}"
                        
                        self.message_queue.put(("log", log_message))
                        
                    except json.JSONDecodeError:
                        continue
            
            if updated_count > 0:
                self.message_queue.put(("status", f"Updated metadata for {updated_count} videos!"))
                self.message_queue.put(("log", f"\nMetadata updated in: {os.path.join(base_dir, 'metadata.json')}"))
            else:
                self.message_queue.put(("error", "No metadata was updated"))
                
        except Exception as e:
            self.message_queue.put(("error", f"Error updating metadata: {str(e)}"))
    
    def update_existing_metadata(self, base_dir, updated_entry):
        """Update existing entry in metadata.json"""
        json_file = os.path.join(base_dir, "metadata.json")
        
        try:
            metadata = []
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Find and update the existing entry
            for i, item in enumerate(metadata):
                if item.get('id') == updated_entry['id']:
                    # Keep original timestamp if it exists, but update the rest
                    original_timestamp = item.get('original_timestamp', item.get('timestamp', ''))
                    updated_entry['original_timestamp'] = original_timestamp
                    metadata[i] = updated_entry
                    break
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            self.message_queue.put(("error", f"Could not update metadata file: {str(e)}"))
            
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
    
    def shutoff(self):
        self.stop_download()
        self.destroy()

if __name__ == "__main__":
    class StandaloneApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.downloader = SubDownloader(self)
    
    app = StandaloneApp()
    app.mainloop()
