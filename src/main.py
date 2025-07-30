import tkinter as tk
from tkinter import ttk
import threading

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Minimot, Youtube channel and playlist analyzer")
        self.geometry("400x400")
        self.mainframe = ttk.Frame(self, padding="10 10 10 10")
        self.mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.mainframe.columnconfigure(1, weight=1)
        self.mainframe.rowconfigure(8, weight=1)
        
        button_frame = ttk.Frame(self.mainframe)
        button_frame.grid(column=1, row=2, sticky=tk.W, pady=(0, 10))
        
        ttk.Button(button_frame, text="Open Downloader", 
                 command=self.open_downloader).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open Analyzer", 
                 command=self.open_analyzer).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).grid(
            column=1, row=8, sticky=tk.W)

        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)
            
        self.downloader_window = None
        self.analyzer_window = None

    def open_downloader(self):
        if self.downloader_window is None or not self.downloader_window.winfo_exists():
            self.downloader_window = SubtitleDownloader(self)
            self.downloader_window.protocol("WM_DELETE_WINDOW", self.on_downloader_close)
        else:
            self.downloader_window.lift()

    def open_analyzer(self):
        if self.analyzer_window is None or not self.analyzer_window.winfo_exists():
            self.analyzer_window = SearchAnalyzer(self)
            self.analyzer_window.protocol("WM_DELETE_WINDOW", self.on_analyzer_close)
        else:
            self.analyzer_window.lift()
            
    def on_downloader_close(self):
        self.downloader_window.destroy()
        self.downloader_window = None
        
    def on_analyzer_close(self):
        self.analyzer_window.destroy()
        self.analyzer_window = None

if __name__ == "__main__":
    from downloader import SubtitleDownloader
    from search import SearchAnalyzer
    
    app = App()
    app.mainloop()

