import tkinter as tk
from tkinter import ttk
from tkinter.ttk import Style

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ytsubtool")
        self.geometry("400x350")

        style = Style()
        style.configure('TButton', font = ('TkFixedFont', 15, 'bold'))
        style.map('TButton', foreground = [('active', '!disabled', 'lightgreen')],
                     background = [('active', 'black')])
        
        self.mainframe = ttk.Frame(self, padding="10 10 10 10")
        self.mainframe.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=0.9, relheight=0.9)

        ttk.Label(self.mainframe, text="hello!", font=('TkFixedFont', 25, 'bold')
                ).place(relx=0.5, rely=0.0, anchor=tk.CENTER)
        ttk.Label(self.mainframe, text="Download files first then analyze!", font=('TkFixedFont', 15, 'bold')
                ).place(relx=0.5, rely=0.1, anchor=tk.CENTER)
        
        button_frame = ttk.Frame(self.mainframe)
        button_frame.place(relx=0.5, rely=0.4, anchor=tk.CENTER, relwidth=0.8, relheight=0.5)

        ttk.Button(button_frame, text="Open Downloader", style = 'TButton', # Downloader in GUI
                 command=self.open_downloader).place(relx=0.5, rely=0.3, anchor=tk.CENTER, relwidth=1)
        ttk.Button(button_frame, text="Open Analyzer", style = 'TButton', # Analyzer in GUI
                 command=self.open_analyzer).place(relx=0.5, rely=0.6, anchor=tk.CENTER, relwidth=1)
        ttk.Button(button_frame, text="Open First Word Analyzer", style = 'TButton', # First Word Analyzer in GUI
                 command=self.open_firstanalyzer).place(relx=0.5, rely=0.9, anchor=tk.CENTER, relwidth=1)
        
        self.status_var = tk.StringVar()
        ttk.Label(self.mainframe, textvariable=self.status_var).place(
            relx=0.05, rely=0.9, anchor=tk.W)
        
        self.downloader_window = None
        self.analyzer_window = None
        self.firstanalyzer_window = None

    def open_downloader(self):
        if self.downloader_window is None or not self.downloader_window.winfo_exists():
            from dloader import SubDownloader
            self.downloader_window = SubDownloader(self)
            self.downloader_window.protocol("WM_DELETE_WINDOW", self.on_downloader_close)
        else:
            self.downloader_window.lift()

    def open_analyzer(self):
        if self.analyzer_window is None or not self.analyzer_window.winfo_exists():
            from ana import Analyzer
            self.analyzer_window = Analyzer(self)
            self.analyzer_window.protocol("WM_DELETE_WINDOW", self.on_analyzer_close)
        else:
            self.analyzer_window.lift()

    def open_firstanalyzer(self):
        if self.firstanalyzer_window is None or not self.firstanalyzer_window.winfo_exists():
            from first_ana import firstana
            self.firstanalyzer_window = firstana(self)
            self.firstanalyzer_window.protocol("WM_DELETE_WINDOW", self.on_firstanalyzer_close)
        else:
            self.firstanalyzer_window.lift()
            
    def on_downloader_close(self):
        self.downloader_window.destroy()
        self.downloader_window = None
        
    def on_analyzer_close(self):
        self.analyzer_window.destroy()
        self.analyzer_window = None

    def on_firstanalyzer_close(self):
        self.firstanalyzer_window.destroy()
        self.firstanalyzer_window = None

if __name__ == "__main__":
    app = App()
    app.mainloop()
    
# python3 src/app.py