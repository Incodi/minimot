import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
#from analyzer import analyze_vtt_files
from wordcloud_gen import generate_wordcloud

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Channel and Playlist Analyzer")
        self.geometry("1000x800")
        
        # Main frame with padding
        self.mainframe = ttk.Frame(self, padding="10 10 10 10")
        self.mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Configure grid weights
        self.mainframe.columnconfigure(1, weight=1)
        self.mainframe.rowconfigure(8, weight=1)  # Give extra space to the bottom
        
        # URL Entry
        ttk.Label(self.mainframe, text="YouTube Channel URL or Playlist URL:").grid(
            column=1, row=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(self.mainframe, width=60)
        self.url_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Button frame for top buttons
        button_frame = ttk.Frame(self.mainframe)
        button_frame.grid(column=1, row=2, sticky=tk.W, pady=(0, 10))
        
        ttk.Button(button_frame, text="Get VTT Files from channel", 
                  command=self.load_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Download Subtitles", 
                  command=self.download_subtitles).pack(side=tk.LEFT, padx=5)
        
        # Select mode
        ttk.Label(self.mainframe, text="Analysis Mode:").grid(
            column=1, row=3, sticky=tk.W, pady=(10, 5))
        
        self.analysis_mode = tk.StringVar(value="regex")
        mode_frame = ttk.Frame(self.mainframe)
        mode_frame.grid(column=1, row=4, sticky=tk.W, pady=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="Count words with regex", 
                       variable=self.analysis_mode, value="regex").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Search for specific words", 
                       variable=self.analysis_mode, value="specific").pack(side=tk.LEFT, padx=5)
        
        # Target words entry
        ttk.Label(self.mainframe, text="Target Words (comma-separated):").grid(
            column=1, row=5, sticky=tk.W, pady=(10, 5))
        self.words_entry = ttk.Entry(self.mainframe, width=60)
        self.words_entry.grid(column=1, row=6, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Bottom button frame
        bottom_button_frame = ttk.Frame(self.mainframe)
        bottom_button_frame.grid(column=1, row=7, sticky=tk.W, pady=(0, 20))
        
        ttk.Button(bottom_button_frame, text="Run Analysis", 
                  command=self.run_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_button_frame, text="Generate Word Cloud", 
                  command=self.make_wordcloud).pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).grid(
            column=1, row=8, sticky=tk.W)
        
        # Add padding to all widgets
        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def load_files(self):
        self.files = filedialog.askopenfilenames(filetypes=[("VTT files", "*.vtt")])
        if self.files:
            self.status_var.set(f"Loaded {len(self.files)} VTT files")
    
    def download_subtitles(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube channel handle or playlist URL")
            return
    
        # Get the project root directory (one level up from src)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, "data", "input", "vtt_files")
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
        try:
            command = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--convert-subs", "srt",
                "--download-archive", "archive.txt",
                "-o", output_template,
                url
            ]
            subprocess.run(command, check=True)
            self.status_var.set("Subtitles downloaded successfully!")
            messagebox.showinfo("Success", "Subtitles downloaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.status_var.set("Error downloading subtitles")
    
    def run_analysis(self):
        if not hasattr(self, 'files') or not self.files:
            messagebox.showerror("Error", "Please select VTT files first")
            return
            
        if self.analysis_mode.get() == "specific":
            target_words = [w.strip() for w in self.words_entry.get().split(",")]
            if not target_words:
                messagebox.showerror("Error", "Please enter target words")
                return
        else:
            target_words = None  # or implement regex pattern
        
        # analyze_vtt_files(self.files, target_words, self.analysis_mode.get())
        self.status_var.set(f"Analysis complete (mode: {self.analysis_mode.get()})")
        messagebox.showinfo("Info", "Analysis would run here with mode: " + self.analysis_mode.get())
    
    def make_wordcloud(self):
        if not hasattr(self, 'files') or not self.files:
            messagebox.showerror("Error", "Please select VTT files first")
            return
        generate_wordcloud(self.files)
        self.status_var.set("Word cloud generated")

if __name__ == "__main__":
    app = App()
    app.mainloop()