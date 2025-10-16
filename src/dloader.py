import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import re
import json
from datetime import datetime, timedelta
import threading
import queue


class SubDownloader(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Subtitle Downloader")
        self.geometry("1000x700")
        self.download_limit = 300
        self.total_downloaded = 0
        self.download_thread = None
        self.stop_event = threading.Event()
        self.message_queue = queue.Queue()
        
        self.setup_ui()
        self.after(100, self.process_queue)
    
    def setup_ui(self):
        """Setup all UI components"""
        self.mainframe = ttk.Frame(self, padding="20")
        self.mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # URL entry
        ttk.Label(self.mainframe, text="YouTube Channel URL or Playlist URL:").grid(
            column=0, row=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(self.mainframe, width=100)
        self.url_entry.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Metadata-only checkbox
        self.metadata_only_var = tk.BooleanVar()
        ttk.Checkbutton(
            self.mainframe, 
            text="Update metadata only (don't download new subtitles)", 
            variable=self.metadata_only_var
        ).grid(column=0, row=2, sticky=tk.W, pady=(5, 10))
        
        # Download button
        self.download_button = ttk.Button(
            self.mainframe, 
            text="Download Subtitles", 
            command=self.start_download
        )
        self.download_button.grid(column=0, row=3, sticky=tk.W, pady=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.mainframe, 
            orient='horizontal', 
            length=400, 
            mode='determinate'
        )
        self.progress.grid(column=0, row=4, sticky=tk.W, pady=(10, 0))
        
        # Status label
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).grid(
            column=0, row=5, sticky=tk.W, pady=(10, 0))
        
        # Output text
        self.text_output = tk.Text(self.mainframe, height=30, wrap=tk.WORD)
        self.text_output.grid(column=0, row=6, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        scrollbar = ttk.Scrollbar(
            self.mainframe, 
            orient=tk.VERTICAL, 
            command=self.text_output.yview
        )
        scrollbar.grid(column=1, row=6, sticky=(tk.N, tk.S))
        self.text_output['yscrollcommand'] = scrollbar.set
    
    def start_download(self):
        """Start download in background thread"""
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Warning", "Download is already in progress!")
            return
        
        self.stop_event.clear()
        self.download_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.text_output.delete(1.0, tk.END)
        self.total_downloaded = 0
        
        button_text = "Updating Metadata..." if self.metadata_only_var.get() else "Downloading..."
        self.download_button.config(text=button_text)
        
        self.download_thread = threading.Thread(target=self.download_subtitles, daemon=True)
        self.download_thread.start()
    
    def download_subtitles(self):
        """Main download logic"""
        url = self.url_entry.get().strip()
        if not url:
            self.queue_message("error", "Please enter a YouTube channel or playlist URL!")
            return
        
        try:
            identifier = self.extract_identifier(url)
            channel_name = self.extract_channel_name(url)
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "input", identifier
            )
            
            if self.metadata_only_var.get():
                self.handle_metadata_update(base_dir, channel_name)
            else:
                self.handle_subtitle_download(base_dir, channel_name, url)
                
        except Exception as e:
            self.queue_message("error", f"Unexpected error: {str(e)}")
        finally:
            self.queue_message("done", None)
    
    def handle_metadata_update(self, base_dir, channel_name):
        """Handle metadata-only update mode"""
        if not os.path.exists(base_dir) or not os.path.exists(os.path.join(base_dir, "metadata.json")):
            self.queue_message("error", f"No previous downloads found. Directory: {base_dir}")
            return
        
        videos_to_update = self.get_outdated_videos(base_dir)
        if not videos_to_update:
            self.queue_message("status", "All metadata is up to date (updated within 7 days)")
            return
        
        self.queue_message("status", f"{len(videos_to_update)} videos need metadata updates")
        self.update_metadata_batch(videos_to_update, base_dir, channel_name)
    
    def handle_subtitle_download(self, base_dir, channel_name, url):
        """Handle normal subtitle download mode"""
        vtt_dir = os.path.join(base_dir, "vtt_files")
        os.makedirs(vtt_dir, exist_ok=True)
        
        command = [
            "yt-dlp",
            "--write-auto-sub", "--sub-lang", "en", "--skip-download",
            "--convert-subs", "vtt", "--print-json",
            "--download-archive", os.path.join(base_dir, "archive.txt"),
            "--no-warnings", "--force-write-archive", "--no-overwrites",
            "--sleep-subtitles", "1",
            "--extractor-args", "youtube:player-client=default,mweb",
            "-o", os.path.join(vtt_dir, "%(title)s [%(id)s].%(ext)s"),
            "--max-downloads", str(self.download_limit),
            url
        ]
        
        self.queue_message("status", f"Starting download (max {self.download_limit} subtitles)...")
        self.run_download_process(command, base_dir, channel_name)
    
    def run_download_process(self, command, base_dir, channel_name):
        """Run yt-dlp process and handle output"""
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        while True:
            if self.stop_event.is_set():
                process.terminate()
                self.queue_message("status", "Download stopped by user")
                break
            
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            
            try:
                video_data = json.loads(line)
                if video_data.get('_type') == 'playlist':
                    continue
                
                self.process_video_data(video_data, base_dir, channel_name)
                
                if self.total_downloaded >= self.download_limit:
                    process.terminate()
                    break
            except json.JSONDecodeError:
                continue
        
        self.finalize_download(process)
    
    def process_video_data(self, data, base_dir, channel_name):
        """Process and save video data"""
        entry = {
            'id': data.get('id', ''),
            'title': data.get('title', ''),
            'url': data.get('webpage_url', ''),
            'upload_date': data.get('upload_date', ''),
            'duration': data.get('duration', 0),
            'view_count': data.get('view_count', 0),
            'like_count': data.get('like_count', 0),
            'comment_count': data.get('comment_count', 0),
            'was_live': data.get('was_live', False),
            'is_live': data.get('is_live', False),
            'timestamp': datetime.now().isoformat(),
            'channel_name': channel_name or data.get('channel', ''),
            'channel_id': data.get('channel_id', ''),
            'channel_url': data.get('channel_url', ''),
            'subscriber_count': data.get('channel_follower_count', 0)
        }
        
        self.save_metadata(base_dir, entry)
        self.total_downloaded += 1
        
        progress = (self.total_downloaded / self.download_limit) * 100
        self.queue_message("progress", progress)
        self.queue_message("log", self.format_log_message(entry))
    
    def update_metadata_batch(self, videos, base_dir, channel_name):
        """Update metadata for multiple videos in batches"""
        updated_count = 0
        batch_size = 50
        total = len(videos)
        
        for i in range(0, total, batch_size):
            if self.stop_event.is_set():
                break
            
            batch = videos[i:i+batch_size]
            urls = [f"https://www.youtube.com/watch?v={v['id']}" for v in batch]
            
            command = [
                "yt-dlp", "--skip-download", "--print-json",
                "--no-warnings", "--extractor-args", "youtube:player-client=default,mweb"
            ] + urls
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            for line in process.stdout:
                if self.stop_event.is_set():
                    process.terminate()
                    break
                
                try:
                    data = json.loads(line)
                    if data.get('_type') == 'playlist':
                        continue
                    
                    original = next((v for v in batch if v['id'] == data.get('id')), None)
                    entry = self.build_metadata_entry(data, channel_name, original)
                    
                    self.update_existing_metadata(base_dir, entry)
                    updated_count += 1
                    
                    self.queue_message("progress", (updated_count / total) * 100)
                    self.queue_message("log", self.format_update_message(entry, original))
                except json.JSONDecodeError:
                    continue
        
        msg = f"✓ Updated metadata for {updated_count}/{total} videos" if updated_count > 0 else "No metadata was updated"
        self.queue_message("status", msg)
    
    def build_metadata_entry(self, data, channel_name, original):
        """Build metadata entry from video data"""
        return {
            'id': data.get('id', ''),
            'title': data.get('title', ''),
            'url': data.get('webpage_url', ''),
            'upload_date': data.get('upload_date', ''),
            'duration': data.get('duration', 0),
            'view_count': data.get('view_count', 0),
            'like_count': data.get('like_count', 0),
            'comment_count': data.get('comment_count', 0),
            'was_live': data.get('was_live', False),
            'is_live': data.get('is_live', False),
            'timestamp': datetime.now().isoformat(),
            'channel_name': channel_name or data.get('channel', ''),
            'channel_id': data.get('channel_id', ''),
            'channel_url': data.get('channel_url', ''),
            'subscriber_count': data.get('channel_follower_count', 0),
            'original_timestamp': original.get('last_updated', '') if original else ''
        }
    
    def get_outdated_videos(self, base_dir):
        """Get videos with metadata older than 7 days"""
        json_file = os.path.join(base_dir, "metadata.json")
        if not os.path.exists(json_file):
            return []
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return [
                {'id': item['id'], 'title': item.get('title', 'Unknown'), 'last_updated': item.get('timestamp', '')}
                for item in metadata
                if 'id' in item and self.is_outdated(item.get('timestamp', ''))
            ]
        except Exception as e:
            self.queue_message("error", f"Error reading metadata: {str(e)}")
            return []
    
    def is_outdated(self, timestamp_str, days=7):
        """Check if timestamp is older than specified days"""
        try:
            last_update = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            if last_update.tzinfo:
                last_update = last_update.replace(tzinfo=None)
            return (datetime.now() - last_update) > timedelta(days=days)
        except (ValueError, TypeError, AttributeError):
            return True
    
    def save_metadata(self, base_dir, entry):
        """Add new entry to metadata.json"""
        json_file = os.path.join(base_dir, "metadata.json")
        
        try:
            metadata = []
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            if entry['id'] not in {item.get('id') for item in metadata}:
                metadata.append(entry)
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
        except Exception as e:
            self.queue_message("error", f"Could not update metadata: {str(e)}")
    
    def update_existing_metadata(self, base_dir, entry):
        """Update existing entry in metadata.json"""
        json_file = os.path.join(base_dir, "metadata.json")
        
        try:
            metadata = []
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            for i, item in enumerate(metadata):
                if item.get('id') == entry['id']:
                    if 'original_timestamp' not in item and 'timestamp' in item:
                        entry['original_timestamp'] = item['timestamp']
                    elif 'original_timestamp' in item:
                        entry['original_timestamp'] = item['original_timestamp']
                    metadata[i] = entry
                    break
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            self.queue_message("error", f"Could not update metadata: {str(e)}")
    
    def finalize_download(self, process):
        """Handle download completion"""
        if self.total_downloaded > 0:
            identifier = self.extract_identifier(self.url_entry.get().strip())
            self.queue_message("status", f"✓ Downloaded {self.total_downloaded} subtitles to {identifier}")
        else:
            error = process.stderr.read()
            msg = f"No subtitles downloaded. Error: {error[:200]}" if error else "No new subtitles found (may already be downloaded)"
            self.queue_message("error" if error else "status", msg)
    
    def format_log_message(self, entry):
        """Format log message for downloaded video"""
        status = []
        if entry['is_live']:
            status.append("LIVE")
        elif entry['was_live']:
            status.append("Was Live")
        
        status_str = f" [{', '.join(status)}]" if status else ""
        date_str = self.format_date(entry['upload_date'])
        
        msg = f"Downloaded: {entry['title']}{status_str} ({date_str})"
        if entry['view_count']:
            msg += f" | Views: {self.format_count(entry['view_count'])}"
        if entry['like_count']:
            msg += f" | Likes: {self.format_count(entry['like_count'])}"
        return msg
    
    def format_update_message(self, entry, original):
        """Format log message for metadata update"""
        status = []
        if entry['is_live']:
            status.append("LIVE")
        elif entry['was_live']:
            status.append("Was Live")
        
        status_str = f" [{', '.join(status)}]" if status else ""
        days = self.get_days_since(original.get('last_updated', '')) if original else "?"
        
        msg = f"Updated: {entry['title']}{status_str} ({days} days old)"
        if entry['view_count']:
            msg += f" | Views: {self.format_count(entry['view_count'])}"
        if entry['like_count']:
            msg += f" | Likes: {self.format_count(entry['like_count'])}"
        return msg
    
    def format_date(self, date_str):
        """Format YYYYMMDD to YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return date_str
    
    def format_count(self, count):
        """Format numbers with K/M/B suffixes"""
        if not count:
            return "0"
        try:
            count = int(count)
            if count >= 1_000_000_000:
                return f"{count / 1_000_000_000:.1f}B"
            elif count >= 1_000_000:
                return f"{count / 1_000_000:.1f}M"
            elif count >= 1_000:
                return f"{count / 1_000:.1f}K"
            return str(count)
        except (ValueError, TypeError):
            return "N/A"
    
    def get_days_since(self, timestamp_str):
        """Calculate days since timestamp"""
        try:
            last_update = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            if last_update.tzinfo:
                last_update = last_update.replace(tzinfo=None)
            return (datetime.now() - last_update).days
        except (ValueError, TypeError, AttributeError):
            return "?"
    
    def extract_identifier(self, url):
        """Extract channel/playlist identifier from URL"""
        patterns = [
            r'youtube\.com/c/([^/]+)',
            r'youtube\.com/channel/([^/]+)',
            r'youtube\.com/@([^/]+)',
            r'youtube\.com/user/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        playlist_match = re.search(r'[&?]list=([^&]+)', url)
        return playlist_match.group(1) if playlist_match else "youtube_subtitles"
    
    def extract_channel_name(self, url):
        """Extract channel name from URL"""
        patterns = [
            r'youtube\.com/c/([^/]+)',
            r'youtube\.com/channel/([^/]+)',
            r'youtube\.com/@([^/]+)',
            r'youtube\.com/user/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def queue_message(self, msg_type, content):
        """Add message to queue for UI updates"""
        self.message_queue.put((msg_type, content))
    
    def process_queue(self):
        """Process message queue for UI updates"""
        try:
            while True:
                msg_type, content = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self.status_var.set(content)
                elif msg_type == "progress":
                    self.progress['value'] = content
                elif msg_type == "log":
                    self.text_output.insert(tk.END, content + "\n")
                    self.text_output.see(tk.END)
                elif msg_type == "error":
                    messagebox.showerror("Error", content)
                elif msg_type == "done":
                    self.download_button.config(state=tk.NORMAL, text="Download Subtitles")
                    break
        except queue.Empty:
            pass
        
        self.after(100, self.process_queue)


if __name__ == "__main__":
    class StandaloneApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.downloader = SubDownloader(self)
    
    app = StandaloneApp()
    app.mainloop()
