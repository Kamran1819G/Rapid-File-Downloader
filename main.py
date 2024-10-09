import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import os
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import time
import re


class AdvancedParallelIDM:
    def __init__(self, master):
        self.master = master
        master.title("Internet Download Manager - by Kamran Khan")
        master.geometry("1000x800")

        self.create_widgets()
        self.load_config()

        self.download_paused = False
        self.download_completed = False
        self.download_cancelled = False
        self.segment_progress = []
        self.total_downloaded = 0
        self.download_speed = 0
        self.start_time = 0
        self.download_threads = []
        self.total_size = 0
        self.current_url = ""

    def create_widgets(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # URL and Path Frame
        self.url_path_frame = ttk.Frame(self.main_frame)
        self.url_path_frame.pack(fill=tk.X, pady=5)

        self.url_label = ttk.Label(self.url_path_frame, text="URL:")
        self.url_label.grid(row=0, column=0, sticky="w", padx=(0, 5))

        self.url_entry = ttk.Entry(self.url_path_frame, width=70)
        self.url_entry.grid(row=0, column=1, sticky="we", padx=(0, 5))
        self.url_entry.bind(
            '<Return>', lambda event: self.find_downloadable_files())

        self.path_label = ttk.Label(self.url_path_frame, text="Save to:")
        self.path_label.grid(row=1, column=0, sticky="w",
                             padx=(0, 5), pady=(5, 0))

        self.path_entry = ttk.Entry(self.url_path_frame, width=60)
        self.path_entry.grid(row=1, column=1, sticky="we",
                             padx=(0, 5), pady=(5, 0))

        self.browse_button = ttk.Button(
            self.url_path_frame, text="Browse", command=self.browse_path)
        self.browse_button.grid(row=1, column=2, sticky="e", pady=(5, 0))

        self.url_path_frame.columnconfigure(1, weight=1)

        # Options Frame
        self.options_frame = ttk.Frame(self.main_frame)
        self.options_frame.pack(fill=tk.X, pady=10)

        self.auto_segment_var = tk.BooleanVar(value=True)
        self.auto_segment_check = ttk.Checkbutton(
            self.options_frame, text="Auto Segment", variable=self.auto_segment_var)
        self.auto_segment_check.pack(side=tk.LEFT)

        self.segments_label = ttk.Label(self.options_frame, text="Segments:")
        self.segments_label.pack(side=tk.LEFT, padx=(10, 5))

        self.segments_entry = ttk.Entry(self.options_frame, width=5)
        self.segments_entry.insert(0, "8")
        self.segments_entry.pack(side=tk.LEFT)

        self.find_files_button = ttk.Button(
            self.options_frame, text="Find Files", command=self.find_downloadable_files)
        self.find_files_button.pack(side=tk.RIGHT)

        self.download_button = ttk.Button(
            self.options_frame, text="Download", command=self.start_download, state=tk.DISABLED)
        self.download_button.pack(side=tk.RIGHT, padx=(0, 5))

        self.pause_resume_button = ttk.Button(
            self.options_frame, text="Pause/Resume", command=self.toggle_pause_resume, state=tk.DISABLED)
        self.pause_resume_button.pack(side=tk.RIGHT, padx=(0, 5))

        self.cancel_button = ttk.Button(
            self.options_frame, text="Cancel", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.RIGHT, padx=(0, 5))

        # File List Frame
        self.file_list_frame = ttk.LabelFrame(
            self.main_frame, text="Downloadable Files")
        self.file_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.file_listbox = tk.Listbox(
            self.file_list_frame, height=5, selectmode=tk.SINGLE)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        self.file_scrollbar = ttk.Scrollbar(
            self.file_list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=self.file_scrollbar.set)

        # Progress Frame
        self.progress_frame = ttk.LabelFrame(
            self.main_frame, text="Download Progress")
        self.progress_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.overall_progress_bar = ttk.Progressbar(
            self.progress_frame, length=700, mode='determinate')
        self.overall_progress_bar.pack(fill=tk.X, padx=5, pady=5)

        self.overall_progress_label = ttk.Label(
            self.progress_frame, text="Overall: 0%")
        self.overall_progress_label.pack(pady=(0, 5))

        self.segment_progress_canvas = tk.Canvas(self.progress_frame)
        self.segment_progress_canvas.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.segment_progress_scrollbar = ttk.Scrollbar(
            self.progress_frame, orient=tk.VERTICAL, command=self.segment_progress_canvas.yview)
        self.segment_progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.segment_progress_frame = ttk.Frame(self.segment_progress_canvas)
        self.segment_progress_canvas.create_window(
            (0, 0), window=self.segment_progress_frame, anchor=tk.NW)

        self.segment_progress_frame.bind("<Configure>", lambda e: self.segment_progress_canvas.configure(
            scrollregion=self.segment_progress_canvas.bbox("all")))
        self.segment_progress_canvas.configure(
            yscrollcommand=self.segment_progress_scrollbar.set)

        # Status and Details Frame
        self.status_details_frame = ttk.Frame(self.main_frame)
        self.status_details_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.status_label = ttk.Label(self.status_details_frame, text="")
        self.status_label.pack(fill=tk.X, pady=5)

        self.details_text = tk.Text(
            self.status_details_frame, height=10, width=120)
        self.details_text.pack(fill=tk.BOTH, expand=True, pady=5)

    def load_config(self):
        try:
            with open('idm_config.json', 'r') as f:
                config = json.load(f)
                self.path_entry.insert(0, config.get('default_path', ''))
        except FileNotFoundError:
            pass

    def save_config(self):
        config = {
            'default_path': self.path_entry.get()
        }
        with open('idm_config.json', 'w') as f:
            json.dump(config, f)

    def browse_path(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder_selected)
            self.save_config()

    def find_downloadable_files(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        self.status_label.config(text="Analyzing URL...")
        self.file_listbox.delete(0, tk.END)
        self.master.update()

        try:
            response = requests.head(url, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()

            if 'text/html' not in content_type:
                # This is likely a direct file link
                file_name = os.path.basename(urlparse(url).path)
                self.file_listbox.insert(tk.END, f"{file_name} ({url})")
                self.current_url = url
                self.download_button.config(state=tk.NORMAL)
                self.status_label.config(
                    text="Direct file link detected. Ready to download.")
                return

            # If it's an HTML page, proceed with the original logic
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')

            downloadable_extensions = [
                '.pdf', '.zip', '.exe', '.mp3', '.mp4', '.avi', '.mov', '.docx', '.xlsx', '.pptx']
            found_files = []

            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    file_name = os.path.basename(urlparse(full_url).path)
                    if any(file_name.lower().endswith(ext) for ext in downloadable_extensions):
                        found_files.append((file_name, full_url))

            for file_name, full_url in found_files:
                self.file_listbox.insert(tk.END, f"{file_name} ({full_url})")

            if not found_files:
                self.status_label.config(text="No downloadable files found.")
            else:
                self.status_label.config(
                    text=f"Found {len(found_files)} downloadable file(s).")
                self.file_listbox.selection_set(0)
                self.on_file_select(None)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze URL: {str(e)}")
            self.status_label.config(
                text="Error occurred while analyzing URL.")

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            file_info = self.file_listbox.get(selection[0])
            file_url = re.search(r'\((.*?)\)$', file_info).group(1)
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, file_url)
            self.current_url = file_url
            self.download_button.config(state=tk.NORMAL)

    def start_download(self):
        url = self.current_url
        save_path = self.path_entry.get()

        if not url or not save_path:
            messagebox.showerror(
                "Error", "Please select a file and specify a save path")
            return

        self.download_paused = False
        self.download_completed = False
        self.download_cancelled = False
        self.pause_resume_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.DISABLED)

        if self.auto_segment_var.get():
            segments = self.auto_segment(url)
        else:
            segments = int(self.segments_entry.get())

        self.segment_progress = [0] * segments
        self.total_downloaded = 0
        self.start_time = time.time()

        # Clear previous progress bars
        for widget in self.segment_progress_frame.winfo_children():
            widget.destroy()

        # Create new progress bars
        self.segment_progress_bars = []
        self.segment_progress_labels = []
        for i in range(segments):
            frame = ttk.Frame(self.segment_progress_frame)
            frame.pack(fill=tk.X, pady=2)

            progress_bar = ttk.Progressbar(
                frame, length=100, mode='determinate')
            progress_bar.pack(side=tk.LEFT, expand=True, fill=tk.X)
            self.segment_progress_bars.append(progress_bar)

            progress_label = ttk.Label(frame, text=f"S{i+1}: 0%")
            progress_label.pack(side=tk.LEFT, padx=(5, 0))
            self.segment_progress_labels.append(progress_label)

        self.download_threads = []
        for i in range(segments):
            thread = threading.Thread(
                target=self.download_segment, args=(url, save_path, i, segments))
            self.download_threads.append(thread)
            thread.start()

        self.master.after(100, self.update_ui)

    def auto_segment(self, url):
        try:
            response = requests.head(url)
            self.total_size = int(response.headers.get('content-length', 0))
            if self.total_size > 100 * 1024 * 1024:  # If file is larger than 100MB
                return 16  # Use 16 segments for large files
            elif self.total_size > 50 * 1024 * 1024:  # If file is larger than 50MB
                return 8  # Use 8 segments for medium files
            else:
                return 4  # Use 4 segments for small files
        except:
            return 8  # Default to 8 segments if unable to determine file size

    def download_segment(self, url, save_path, segment_index, total_segments):
        try:
            if self.total_size == 0:
                response = requests.head(url)
                self.total_size = int(
                    response.headers.get('content-length', 0))

            segment_size = self.total_size // total_segments
            start = segment_index * segment_size
            end = start + segment_size - 1 if segment_index < total_segments - \
                1 else self.total_size - 1
            headers = {'Range': f'bytes={start}-{end}'}
            response = requests.get(url, headers=headers, stream=True)

            file_name = os.path.join(save_path, f"{os.path.basename(
                urlparse(url).path)}.part{segment_index}")
            with open(file_name, 'wb') as file:
                downloaded = 0
                for data in response.iter_content(chunk_size=1024):
                    while self.download_paused:
                        time.sleep(0.1)
                    if self.download_cancelled:
                        return
                    size = file.write(data)
                    downloaded += size
                    self.segment_progress[segment_index] = downloaded
                    self.total_downloaded += size

        except Exception as e:
            print(f"Error in download segment {segment_index}: {str(e)}")

    def update_ui(self):
        if not self.download_completed and not self.download_cancelled:
            overall_progress = (
                self.total_downloaded / self.total_size) * 100 if self.total_size > 0 else 0
            self.overall_progress_bar['value'] = overall_progress
            self.overall_progress_label.config(
                text=f"Overall: {overall_progress:.1f}%")

            segment_size = self.total_size // len(self.segment_progress)
            for i, (progress_bar, progress_label) in enumerate(zip(self.segment_progress_bars, self.segment_progress_labels)):
                segment_progress = (
                    self.segment_progress[i] / segment_size) * 100
                progress_bar['value'] = segment_progress
                progress_label.config(text=f"S{i+1}: {segment_progress:.1f}%")

            elapsed_time = time.time() - self.start_time
            self.download_speed = self.total_downloaded / \
                (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0

            self.update_details()

            if all(thread.is_alive() == False for thread in self.download_threads):
                self.download_completed = True
                self.combine_segments()
                self.status_label.config(text="Download completed!")
                self.pause_resume_button.config(state=tk.DISABLED)
                self.cancel_button.config(state=tk.DISABLED)
                self.download_button.config(state=tk.NORMAL)
            else:
                self.master.after(100, self.update_ui)
        elif self.download_cancelled:
            self.status_label.config(text="Download cancelled.")
            self.pause_resume_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            self.download_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Download completed!")
            self.pause_resume_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            self.download_button.config(state=tk.NORMAL)

    def update_details(self):
        details = f"Download Speed: {self.download_speed:.2f} MB/s\n"
        details += f"Total Downloaded: {
            self.total_downloaded / (1024 * 1024):.2f} MB\n"
        details += f"Total Size: {self.total_size / (1024 * 1024):.2f} MB\n"
        details += f"Elapsed Time: {time.time() -
                                    self.start_time:.2f} seconds\n"
        details += f"Estimated Time Remaining: {
            self.estimate_time_remaining():.2f} seconds\n"
        details += "Segment Progress:\n"
        segment_size = self.total_size // len(self.segment_progress)
        for i, progress in enumerate(self.segment_progress):
            segment_progress = (progress / segment_size) * 100
            details += f"  Segment {i+1}: {progress / (1024 * 1024):.2f} MB / {
                segment_size / (1024 * 1024):.2f} MB ({segment_progress:.1f}%)\n"

        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)

    def estimate_time_remaining(self):
        if self.download_speed > 0:
            remaining_size = self.total_size - self.total_downloaded
            return remaining_size / (self.download_speed * 1024 * 1024)
        return 0

    def toggle_pause_resume(self):
        self.download_paused = not self.download_paused
        if self.download_paused:
            self.pause_resume_button.config(text="Resume")
            self.status_label.config(text="Download paused")
        else:
            self.pause_resume_button.config(text="Pause")
            self.status_label.config(text="Download resumed")

    def cancel_download(self):
        self.download_cancelled = True
        for thread in self.download_threads:
            thread.join()  # Wait for all threads to finish
        self.status_label.config(text="Cancelling download...")
        self.clean_up_partial_files()
        self.reset_ui()

    def clean_up_partial_files(self):
        save_path = self.path_entry.get()
        base_name = os.path.basename(urlparse(self.current_url).path)
        for i in range(len(self.segment_progress)):
            partial_file = os.path.join(save_path, f"{base_name}.part{i}")
            if os.path.exists(partial_file):
                os.remove(partial_file)

    def reset_ui(self):
        self.overall_progress_bar['value'] = 0
        self.overall_progress_label.config(text="Overall: 0%")
        for progress_bar, progress_label in zip(self.segment_progress_bars, self.segment_progress_labels):
            progress_bar['value'] = 0
            progress_label.config(text="0%")
        self.details_text.delete(1.0, tk.END)
        self.status_label.config(text="Download cancelled")
        self.download_button.config(state=tk.NORMAL)
        self.pause_resume_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

    def combine_segments(self):
        url = self.current_url
        save_path = self.path_entry.get()
        file_name = os.path.join(
            save_path, os.path.basename(urlparse(url).path))

        with open(file_name, 'wb') as output_file:
            for i in range(len(self.segment_progress)):
                segment_file = f"{file_name}.part{i}"
                with open(segment_file, 'rb') as segment:
                    output_file.write(segment.read())
                os.remove(segment_file)

        self.status_label.config(
            text="Download completed and segments combined!")


if __name__ == "__main__":
    root = tk.Tk()
    idm = AdvancedParallelIDM(root)
    root.mainloop()
