import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, re, json, webbrowser, random, subprocess, sys
from datetime import datetime
from collections import defaultdict
from importlib.metadata import distributions
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
from searchhelper import (
    hms_to_seconds, seconds_to_hms, is_valid_date, process_search_query, 
    matches_search_terms, check_requirements, extract_video_id
)

# Find Wordcloud and Treemap
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

try:
    import squarify
    SQUARIFY_AVAILABLE = True
except ImportError:
    SQUARIFY_AVAILABLE = False


class firstana(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("First Words")
        self.geometry("1600x1000")
        self.video_metadata = []
        self.current_stats = {}
        self.check_requirements()
        self.setup_ui()
        
    def setup_ui(self):
        self.mainframe = ttk.Frame(self, padding=10)
        self.mainframe.grid(column=0, row=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self.mainframe)
        left.grid(column=0, row=0, sticky="nsew", padx=10)
        
        ttk.Label(left, text="Folder name (Channel handle or Playlist ID)").grid(column=0, row=0, sticky="w", pady=(0,5))
        self.url_entry = ttk.Entry(left, width=60)
        self.url_entry.grid(column=0, row=1, sticky="we", pady=(0,10))
        
        btn_frame = ttk.Frame(left)
        btn_frame.grid(column=0, row=2, sticky="w", pady=(0,10))
        
        ttk.Button(btn_frame, text="Convert VTTs", command=self.convert_vtt_to_txt).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Edit Stopwords", command=self.edit_stopwords).pack(side="left", padx=5)
        
        self.use_stopwords = tk.BooleanVar(value=False)
        ttk.Checkbutton(btn_frame, text="Use Stopwords", variable=self.use_stopwords).pack(side="left", padx=5)
        self.no_punctuation = tk.BooleanVar(value=True)
        ttk.Checkbutton(btn_frame, text="No Punctuation", variable=self.no_punctuation).pack(side="left", padx=5)
        
        word_index_frame = ttk.Frame(left)
        word_index_frame.grid(column=0, row=3, sticky="w", pady=(10,5))
        ttk.Label(word_index_frame, text="Word Position Index:").pack(side="left")
        self.word_index = ttk.Entry(word_index_frame, width=10)
        self.word_index.pack(side="left", padx=(5,10))
        ttk.Label(word_index_frame, text="(0=1st, 1=2nd, -1=last, etc. Default: 0)").pack(side="left")
        
        ttk.Label(left, text="Word Filter:").grid(column=0, row=5, sticky="w", pady=(10,5))
        self.words_entry = ttk.Entry(left, width=70)
        self.words_entry.grid(column=0, row=6, sticky="we", pady=(0,20))
        
        right = ttk.Frame(self.mainframe)
        right.grid(column=1, row=0, sticky="nsew", padx=10)
        
        filter_frame = ttk.LabelFrame(right, text="More Filters", padding=10)
        filter_frame.pack(fill="both", expand=True)
        
        filters = [("Title Contains:", "title_filter"), ("Channel Name:", "channel_filter")]
        for i, (label, var_name) in enumerate(filters):
            frame = ttk.Frame(filter_frame)
            frame.pack(fill="x", pady=(0,10))
            ttk.Label(frame, text=label).pack(side="left")
            setattr(self, var_name, ttk.Entry(frame))
            getattr(self, var_name).pack(side="left", expand=True, fill="x", padx=5)
        
        sort_frame = ttk.Frame(filter_frame)
        sort_frame.pack(fill="x", pady=(0,10))
        ttk.Label(sort_frame, text="Sort by:").pack(side="left")
        
        self.sort_var = tk.StringVar(value="title")
        self.sort_direction = tk.StringVar(value="desc")
        
        sort_dir_frame = ttk.Frame(sort_frame)
        sort_dir_frame.pack(side="right")
        ttk.Radiobutton(sort_dir_frame, text="↑", variable=self.sort_direction, value="desc").pack(side="left")
        ttk.Radiobutton(sort_dir_frame, text="↓", variable=self.sort_direction, value="asc").pack(side="left")
        
        for val, text in [("title", "Title"), ("date", "Date"), ("duration", "Duration")]:
            ttk.Radiobutton(sort_frame, text=text, variable=self.sort_var, value=val).pack(side="left", padx=5)
        
        date_frame = ttk.Frame(filter_frame)
        date_frame.pack(fill="x", pady=(0,10))
        ttk.Label(date_frame, text="Date Range:").pack(side="left")
        
        for label, var in [("From:", "date_from"), ("To:", "date_to")]:
            frame = ttk.Frame(date_frame)
            frame.pack(side="left", padx=(5,0))
            ttk.Label(frame, text=label).pack(side="left")
            setattr(self, var, ttk.Entry(frame, width=10))
            getattr(self, var).pack(side="left")
        
        dur_frame = ttk.Frame(filter_frame)
        dur_frame.pack(fill="x", pady=(0,10))
        ttk.Label(dur_frame, text="Duration:").pack(side="left")
        
        for label, var in [("Min:", "duration_min"), ("Max:", "duration_max")]:
            ttk.Label(dur_frame, text=label).pack(side="left", padx=(5,0))
            setattr(self, var, ttk.Entry(dur_frame, width=8))
            getattr(self, var).pack(side="left")
            ttk.Label(dur_frame, text="(HH:MM:SS)").pack(side="left", padx=(0,5))
        
        self.tree = ttk.Treeview(self.mainframe, columns=('details', 'duration', 'date'), height=15)
        self.tree.grid(column=0, row=8, columnspan=2, sticky="nsew")
        self.tree.column('#0', width=500, anchor="w", stretch=True)
        self.tree.column('details', width=300, anchor="w")
        self.tree.column('duration', width=40, anchor="w")
        self.tree.column('date', width=40, anchor="w")
        self.tree.heading('#0', text='Video')
        self.tree.heading('details', text='Selected Word')
        self.tree.heading('duration', text='Duration')
        self.tree.heading('date', text='Date')
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        vsb = ttk.Scrollbar(self.mainframe, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(column=2, row=8, sticky='ns')

        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.columnconfigure(1, weight=3)
        self.mainframe.columnconfigure(2, weight=0)  
        self.mainframe.rowconfigure(8, weight=1)
        
        bottom_frame = ttk.Frame(self.mainframe)
        bottom_frame.grid(column=0, row=9, columnspan=2, sticky="w", pady=(0,20))
        ttk.Button(bottom_frame, text="Run Analysis", command=self.run_analysis).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Show Top Words (max 5000)", command=self.show_full_stats).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Random Video", command=self.show_random_video).pack(side="left", padx=5)
        
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).grid(column=0, row=10, columnspan=2, sticky="w")
        self.style = ttk.Style()
        self.style.configure('Treeview', rowheight=30, wrap=tk.WORD)

    def check_requirements(self):
        try: return check_requirements()
        except Exception as e:
            if messagebox.showerror("Error", str(e)): sys.exit(1)

    def get_word_index(self):
        index_str = self.word_index.get().strip()
        if not index_str:
            return 0
        try:
            return int(index_str)
        except ValueError:
            messagebox.showerror("Error", "Word index must be a valid integer (e.g., 0, 1, -1)")
            return None

    def get_word_position_label(self, index):
        if index == 0:
            return "1st"
        elif index == 1:
            return "2nd"
        elif index == 2:
            return "3rd"
        elif index == -1:
            return "last"
        elif index == -2:
            return "2nd to last"
        elif index == -3:
            return "3rd to last"
        elif index > 0:
            return f"{index + 1}th"
        else:
            return f"{abs(index)}th from end"

    def show_random_video(self):
        try:
            if not (items := self.tree.get_children()):
                messagebox.showinfo("Random Video", "No videos in the current view")
                return

            item = self.tree.item(random.choice(items), 'text')
            for video in self.video_metadata:
                if f"{video.get('title', '')} - {video.get('channel_name', '')}" == item:
                    if url := video.get('url'): webbrowser.open(url)
                    else: messagebox.showinfo("Random Video", "No URL found")
                    return
            messagebox.showinfo("Random Video", "Couldn't find video URL")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open random video: {str(e)}")

    def on_tree_double_click(self, event):
        if not (item := self.tree.selection()[0]): return
        if item_text := self.tree.item(item, 'text'):
            for video in self.video_metadata:
                if f"{video.get('title', '')} - {video.get('channel_name', '')}" == item_text:
                    webbrowser.open(video.get('url', ''))
                    return

    def edit_stopwords(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "data", "input", "stopwords.txt")
        
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write("# Default stopwords\nthe\nand\nto\nof\na\nin\nis\nit\nyou\nthat\n")
        
        if os.name == 'nt': os.startfile(path)
        else: os.system(f'open "{path}"')

    def convert_vtt_to_txt(self):
        if not (handle := self.url_entry.get().strip()):
            messagebox.showerror("Error", "Please enter a channel handle or playlist ID")
            return
        
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vtt_dir = os.path.join(root, "data", "input", handle, "vtt_files")
        txt_dir = os.path.join(root, "data", "input", handle, "txt_files")
        
        if not os.path.exists(vtt_dir):
            messagebox.showerror("Error", f"Directory not found: {vtt_dir}")
            return

        meta_file = os.path.join(root, "data", "input", handle, "metadata.json")
        if os.path.exists(meta_file):
            with open(meta_file, 'r', encoding='utf-8') as f:
                self.video_metadata = json.load(f)
        
        os.makedirs(txt_dir, exist_ok=True)
        self.txt_files = []
        vtt_files = [f for f in os.listdir(vtt_dir) if f.endswith('.vtt')]
        
        if not vtt_files:
            messagebox.showerror("Error", f"No VTT files found in {vtt_dir}")
            return
        
        stopwords = set()
        if self.use_stopwords.get():
            path = os.path.join(root, "data", "input", "stopwords.txt")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    stopwords.update(line.strip().lower() for line in f if line.strip() and not line.startswith('#'))
        
        for vtt_file in vtt_files:
            try:
                video_id = extract_video_id(vtt_file)
                with open(os.path.join(vtt_dir, vtt_file), 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                cleaned = []
                prev = None
                for line in lines:
                    line = line.strip()
                    if (not line or line == "WEBVTT" or line.startswith(("Kind:", "Language:", "NOTE")) or 
                       re.match(r'^\d{2}:\d{2}:\d{2}\.\d{3}.*$', line)):
                        continue
                    
                    line = line.replace('[&nbsp;__&nbsp;]', 'FUCK')
                    line = re.sub(r'\[(?!&nbsp;__&nbsp;).*?\]', '', line)
                    line = re.sub(r'<.*?>|align:start position:0%|&gt;&gt;|>>|&gt;|<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)
                    line = re.sub(r'^\s*[A-Z]+\s*\d*\s*:\s*', '', line)
                    
                    if self.no_punctuation.get():
                        line = re.sub(r'[^\w\s\']', '', line)
                    if not line: continue
                    
                    if self.use_stopwords.get():
                        words = [word for word in line.split() if word.lower() not in stopwords]
                        line = ' '.join(words)
                        if not line: continue
                    
                    if line != prev:             
                        cleaned.append(line)
                        prev = line

                base = os.path.splitext(vtt_file)[0]
                txt_file = os.path.join(txt_dir, f"{base}.txt")
                
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(cleaned))
                
                self.txt_files.append(txt_file)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to convert {vtt_file}: {str(e)}")
        
        if self.txt_files:
            self.status_var.set(f"Converted {len(self.txt_files)} VTT files to TXT")
            self.vtt_files = [os.path.join(vtt_dir, f) for f in vtt_files]

    def get_video_metadata(self, video_id):
        return next((v for v in self.video_metadata if v['id'] == video_id), None)

    def sort_videos(self, videos):
        reverse = (self.sort_direction.get() == "desc")
        key_map = {
            "date": lambda x: x.get('upload_date', ''),
            "duration": lambda x: x.get('duration', 0),
        }
        return sorted(videos, key=key_map.get(self.sort_var.get(), lambda x: x.get('title', '').lower()), reverse=reverse)

    def filter_videos(self, videos):
        filtered = videos.copy()
        
        if title_filter := self.title_filter.get().strip():
            title_terms = process_search_query(title_filter, mode="general")
            filtered = [v for v in filtered if matches_search_terms(v.get('title', ''), title_terms)]
        
        if channel_filter := self.channel_filter.get().strip():
            channel_terms = process_search_query(channel_filter, mode="general")
            filtered = [v for v in filtered if matches_search_terms(v.get('channel_name', ''), channel_terms)]
        
        if word_filter := self.words_entry.get().strip():
            words = [w.strip().lower() for w in word_filter.split(',')]
            filtered = [v for v in filtered if v.get('selected_word') and v.get('selected_word').lower() in words]
        
        if date_from := self.date_from.get().strip():
            if not is_valid_date(date_from):
                messagebox.showerror("Error", "Invalid 'From' date format. Use YYYY-MM-DD")
                return filtered
            filtered = [v for v in filtered if v.get('upload_date', '') >= date_from.replace("-", "")]

        if date_to := self.date_to.get().strip():
            if not is_valid_date(date_to):
                messagebox.showerror("Error", "Invalid 'To' date format. Use YYYY-MM-DD")
                return filtered
            filtered = [v for v in filtered if v.get('upload_date', '') <= date_to.replace("-", "")]
        
        if duration_min := self.duration_min.get().strip():
            try:
                filtered = [v for v in filtered if v.get('duration', 0) >= hms_to_seconds(duration_min)]
            except ValueError:
                messagebox.showerror("Error", "Invalid minimum duration format")
        
        if duration_max := self.duration_max.get().strip():
            try:
                filtered = [v for v in filtered if v.get('duration', 0) <= hms_to_seconds(duration_max)]
            except ValueError:
                messagebox.showerror("Error", "Invalid maximum duration format")
        
        return filtered
                    
    def run_analysis(self):
        if not hasattr(self, 'txt_files') or not self.txt_files:
            messagebox.showerror("Error", "Please convert VTT files first")
            return
        
        word_index = self.get_word_index()
        if word_index is None:
            return
        
        self.tree.delete(*self.tree.get_children())
        self.word_counts = defaultdict(int)
        
        video_data = []
        for txt_file, vtt_file in zip(self.txt_files, self.vtt_files):
            video_id = extract_video_id(os.path.basename(txt_file))
            meta = self.get_video_metadata(video_id) if video_id else None

            selected_word = self.get_word_at_index(txt_file, word_index)
            if selected_word:
                self.word_counts[selected_word] += 1
            
            video_data.append({
                'txt_file': txt_file,
                'vtt_file': vtt_file,
                'name': os.path.splitext(os.path.basename(txt_file))[0],
                'id': video_id,
                'selected_word': selected_word,
                'title': meta.get('title', os.path.splitext(os.path.basename(txt_file))[0]) if meta else os.path.splitext(os.path.basename(txt_file))[0],
                'upload_date': meta.get('upload_date', '') if meta else '',
                'duration': meta.get('duration', 0) if meta else 0,
                'channel_name': meta.get('channel_name', '') if meta else '',
                'url': meta.get('url', '') if meta else ''
            })
        
        video_data = self.filter_videos(video_data)
        video_data = self.sort_videos(video_data)
        
        position_label = self.get_word_position_label(word_index)
        self.tree.heading('details', text=f'{position_label.capitalize()} Word')
        
        for video in video_data:
            dur_str = seconds_to_hms(video.get('duration', 0))
            date = video.get('upload_date', '')
            if date and len(date) == 8 and '-' not in date:
                date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            
            selected_word = video.get('selected_word', 'No words found')
            
            self.tree.insert('', 'end', text=f"{video['title']} - {video.get('channel_name', '')}", 
                        values=(selected_word, dur_str, date))
        
        filtered_word_counts = defaultdict(int)
        for video in video_data:
            if video.get('selected_word'):
                filtered_word_counts[video['selected_word']] += 1
        
        self.current_stats = {
            'word_counts': dict(filtered_word_counts),
            'total_videos': len(video_data),
            'videos_with_words': len([v for v in video_data if v.get('selected_word')]),
            'word_index': word_index,
            'position_label': position_label
        }
        
        total_videos = len(video_data)
        videos_with_words = len([v for v in video_data if v.get('selected_word')])
        self.status_var.set(f"Analyzed {total_videos} videos, {videos_with_words} have {position_label} words")

    def get_word_at_index(self, txt_file, index):
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    words = content.split()
                    if words:
                        try:
                            word = words[index]
                            # Cleans the word of punctuation
                            clean_word = re.sub(r'[^\w\']', '', word).lower()
                            return clean_word if clean_word else None
                        except IndexError:
                            return None
            return None
        except Exception:
            return None
    
    def show_full_stats(self):                
        if not hasattr(self, 'current_stats'): 
            messagebox.showinfo("Info", "Please run analysis first")
            return
        
        popup = tk.Toplevel(self)
        popup.title(f"Top {self.current_stats['position_label'].capitalize()} Words Statistics")
        popup.geometry("1200x800")

        main_frame = ttk.Frame(popup)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Statistics text
        text = tk.Text(main_frame, wrap=tk.WORD, height=10)
        text.pack(fill="x", pady=(0, 10))

        stats = self.current_stats
        position_label = stats['position_label']
        
        text.insert(tk.END, f"=== {position_label.upper()} WORDS STATISTICS ===\n\n", "title")
        text.insert(tk.END, f"Total videos analyzed: {stats['total_videos']}\n")
        text.insert(tk.END, f"Videos with {position_label} words: {stats['videos_with_words']}\n")
        text.insert(tk.END, f"Unique {position_label} words: {len(stats['word_counts'])}\n")
        text.insert(tk.END, f"Word position index: {stats['word_index']}\n\n")
        
        text.tag_config("title", font=('Arial', 14, 'bold'))
        text.config(state="disabled")

        word_frame = ttk.Frame(main_frame)
        word_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(word_frame)
        scrollbar.pack(side="right", fill="y")

        word_text = tk.Text(word_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=('Courier New', 10))
        word_text.pack(fill="both", expand=True)
        scrollbar.config(command=word_text.yview)

        if stats['word_counts']:
            sorted_words = sorted(stats['word_counts'].items(), key=lambda x: (-x[1], x[0]))[:5000]
            
            total_videos = stats['videos_with_words']
            
            word_text.insert(tk.END, f"TOP {position_label.upper()} WORDS (MAX 5000):\n\n", "header")
            word_text.tag_config("header", font=('Arial', 12, 'bold'))
            
            for i, (word, count) in enumerate(sorted_words, 1):
                pct = (count / total_videos * 100) if total_videos > 0 else 0
                if count == 1:
                    word_text.insert(tk.END, f"{i:4}. {word:<20} {count:>6} video ({pct:.1f}%)\n")
                else:
                    word_text.insert(tk.END, f"{i:4}. {word:<20} {count:>6} videos ({pct:.1f}%)\n")
            
            self.top_words = [word for word, _ in sorted_words]

        graph_frame = ttk.Frame(main_frame)
        graph_frame.pack(fill="x", pady=(10, 0))

        btn_frame = ttk.Frame(graph_frame)
        btn_frame.pack(fill="x")

        def show_bar_graph():
            if not stats['word_counts']:
                messagebox.showinfo("Info", f"No {position_label} word data to graph")
                return

            channel_name = ""
            if self.video_metadata:
                channel_name = self.video_metadata[0].get('channel_name', '')
            
            top_50 = sorted(stats['word_counts'].items(), key=lambda x: (-x[1], x[0]))[:50]
            words, counts = zip(*top_50)
            
            plt.figure(figsize=(14, 8))
            bars = plt.bar(range(len(words)), counts, color='#dabdab', alpha=0.8)
            
            plt.title(f'Top 50 Most Common {position_label.capitalize()} Words - {channel_name}', fontsize=16)
            plt.xlabel(f'{position_label.capitalize()} Words', fontsize=12)
            plt.ylabel('Number of Videos', fontsize=12)
            plt.xticks(range(len(words)), words, rotation=45, ha='right')
            plt.grid(axis='y', alpha=0.3)
            
            for i, (bar, count) in enumerate(zip(bars, counts)):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                        str(count), ha='center', va='bottom')
            
            plt.tight_layout()
            plt.show()

        def show_pie_chart():
            if not stats['word_counts']:
                messagebox.showinfo("Info", f"No {position_label} word data to graph")
                return

            channel_name = ""
            if self.video_metadata:
                channel_name = self.video_metadata[0].get('channel_name', '')
            
            top_15 = sorted(stats['word_counts'].items(), key=lambda x: (-x[1], x[0]))[:25]
            words, counts = zip(*top_15)
            
            plt.figure(figsize=(12, 8))
            
            def format_label(pct, counts):
                total = sum(counts)
                count = int(round(pct/100.*total))
                return f'{count}'
            
            wedges, texts, autotexts = plt.pie(counts, labels=words, autopct=lambda pct: format_label(pct, counts),
                                            startangle=90, textprops={'fontsize': 10})
            
            plt.title(f'Top 25 Most Common {position_label.capitalize()} Words - {channel_name}', fontsize=16)
            
            plt.axis('equal')
            
            plt.tight_layout()
            plt.show()

        def show_treemap():
            if not SQUARIFY_AVAILABLE:
                messagebox.showerror("Error", "Squarify library not available. Install with: pip install squarify")
                return
            if not stats['word_counts']:
                messagebox.showinfo("Info", f"No {position_label} word data to graph")
                return
            
            channel_name = self.video_metadata[0].get('channel_name', '') if self.video_metadata else ""
            top_words = sorted(stats['word_counts'].items(), key=lambda x: (-x[1], x[0]))
            words, counts = zip(*top_words)
            
            fig, ax = plt.subplots(figsize=(20, 15), facecolor='#2e2e2e', dpi=150)
            ax.set_facecolor('#2e2e2e')
            
            squarify.plot(
                sizes=counts,
                color=plt.cm.plasma(np.linspace(0.1, 0.9, len(words))),
                alpha=0.9,
                edgecolor='#1a1a1a',
                linewidth=1.5,
                ax=ax
            )
            
            max_count = max(counts)
            min_count = min(counts)
            
            # Use logarithmic scaling for scaling text
            log_counts = np.log10(counts)
            max_log = np.max(log_counts)
            min_log = np.min(log_counts)
            
            for i, (word, count) in enumerate(top_words):
                rect = ax.patches[i]
                x = rect.get_x() + rect.get_width() / 2
                y = rect.get_y() + rect.get_height() / 2
                
                rect_area = rect.get_width() * rect.get_height()
                max_width_based_size = rect.get_width() * 0.5   
                max_height_based_size = rect.get_height() * 0.2  
                
                if max_log > min_log:
                    log_factor = (np.log10(count) - min_log) / (max_log - min_log)
                else:
                    log_factor = 1
                
                power_factor = log_factor ** 0.6                 
                min_font_size = 2   
                max_font_size = 35  
                size_range = max_font_size - min_font_size
                calculated_size = min_font_size + (size_range * power_factor)
                
                rect_constraint = min(max_width_based_size, max_height_based_size) * 8  
                font_size = min(calculated_size, rect_constraint)

                font_size = max(font_size, 2)  
                
                vertical_spacing = max(0.15, font_size * 0.008)  

                ax.text(x, y - rect.get_height() * vertical_spacing, word,
                        ha='center', va='center',
                        fontsize=font_size, fontweight='bold',
                        color='#f0f0f0', fontfamily='sans-serif')
                
                count_font_size = max(3, font_size * 0.55)
                ax.text(x, y + rect.get_height() * vertical_spacing, f"({count})",
                        ha='center', va='center',
                        fontsize=count_font_size, fontweight='bold',
                        color='#e0e0e0', alpha=1.0)
            
            ax.set_title(f'Top {len(top_words)} {position_label.capitalize()} Words - {channel_name}',
                        fontsize=26, fontweight='bold', pad=25, color='white')
            ax.axis('off')
            plt.tight_layout()
            
            plt.show()

        def copy_words():
            if hasattr(self, 'top_words'):
                self.clipboard_clear()
                self.clipboard_append("\n".join(self.top_words))
                
        def generate_word_cloud():
            if not WORDCLOUD_AVAILABLE:
                messagebox.showerror("Error", "WordCloud library not available. Install with: pip install wordcloud")
                return
                
            if not stats['word_counts']:
                messagebox.showinfo("Info", f"No {position_label} word data to generate word cloud")
                return
            
            try:
                root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                mask_path = os.path.join(root, "data", "pg.png")
                
                mask = None
                if os.path.exists(mask_path):
                    try:
                        mask = np.array(Image.open(mask_path))
                    except Exception:
                        pass  

                font_file_path = os.path.join(root, "data", "Ubuntu-Title.ttf")
                
                wordcloud = WordCloud(
                    font_path = font_file_path,
                    max_font_size=400,
                    relative_scaling=0.4,
                    width=1600, height=1200, 
                    background_color='white', 
                    max_words=500,
                    colormap='tab10_r', 
                    normalize_plurals=False, 
                    mask=mask
                ).generate_from_frequencies(stats['word_counts'])
                
                plt.figure(figsize=(12, 8))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis("off")
                
                channel_name = ""
                if self.video_metadata:
                    channel_name = self.video_metadata[0].get('channel_name', '')
                
                plt.title(f"Word Cloud of {position_label.capitalize()} words - {channel_name}")
                plt.show()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate word cloud: {str(e)}")

        ttk.Button(btn_frame, text="Show Bar Graph", command=show_bar_graph).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Show Pie Chart", command=show_pie_chart).pack(side="left", padx=5)
        
        if SQUARIFY_AVAILABLE:
            ttk.Button(btn_frame, text="Show Treemap", command=show_treemap).pack(side="left", padx=5)
        else:
            ttk.Button(btn_frame, text="Install Treemap", 
                      command=lambda: messagebox.showinfo("Install Squarify", 
                                                       "To use treemaps, install with: pip install squarify")).pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text=f"Copy {position_label.capitalize()} Words List", command=copy_words).pack(side="left", padx=5)
        
        if WORDCLOUD_AVAILABLE:
            ttk.Button(btn_frame, text="Generate Word Cloud", command=generate_word_cloud).pack(side="left", padx=5)
        else:
            ttk.Button(btn_frame, text="Install WordCloud", 
                      command=lambda: messagebox.showinfo("Install WordCloud", 
                                                       "To use word clouds, install with: pip install wordcloud")).pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Close", command=popup.destroy).pack(side="right", padx=5)

        word_text.config(state="disabled")


if __name__ == "__main__":
    class StandaloneApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.analyzer = firstana(self)
    
    app = StandaloneApp()
    app.mainloop()