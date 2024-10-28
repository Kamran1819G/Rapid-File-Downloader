import customtkinter as ctk
from tkinter import filedialog, messagebox
import requests
import threading
import os
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import time
import re

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class RapidFileDownloader:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Rapid File Downloader - by Kamran Khan")
        self.window.geometry("1000x800")

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
        # Main container
        self.main_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # URL Frame
        url_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        url_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(url_frame, text="URL:").pack(side="left", padx=(0, 10))
        self.url_entry = ctk.CTkEntry(url_frame, width=400)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.bind(
            '<Return>', lambda event: self.find_downloadable_files())

        # Path Frame
        path_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(path_frame, text="Save to:").pack(
            side="left", padx=(0, 10))
        self.path_entry = ctk.CTkEntry(path_frame, width=300)
        self.path_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(path_frame, text="Browse", command=self.browse_path,
                      width=100).pack(side="right", padx=(10, 0))

        # Options Frame
        options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=(0, 10))

        self.auto_segment_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_frame, text="Auto Segment",
                        variable=self.auto_segment_var).pack(side="left")

        ctk.CTkLabel(options_frame, text="Segments:").pack(
            side="left", padx=(20, 5))
        self.segments_entry = ctk.CTkEntry(options_frame, width=50)
        self.segments_entry.insert(0, "8")
        self.segments_entry.pack(side="left")

        button_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        button_frame.pack(side="right")

        self.find_button = ctk.CTkButton(
            button_frame, text="Find Files", command=self.find_downloadable_files)
        self.find_button.pack(side="left", padx=5)

        self.download_button = ctk.CTkButton(
            button_frame, text="Download", command=self.start_download, state="disabled")
        self.download_button.pack(side="left", padx=5)

        self.pause_button = ctk.CTkButton(
            button_frame, text="Pause/Resume", command=self.toggle_pause_resume, state="disabled")
        self.pause_button.pack(side="left", padx=5)

        self.cancel_button = ctk.CTkButton(
            button_frame, text="Cancel", command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side="left", padx=5)

        # File List Frame
        file_list_frame = ctk.CTkFrame(self.main_frame)
        file_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(file_list_frame, text="Downloadable Files").pack()

        self.file_listbox = ctk.CTkTextbox(file_list_frame, height=100)
        self.file_listbox.pack(fill="both", expand=True)

        # Progress Frame
        progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        progress_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(progress_frame, text="Overall Progress").pack()

        self.overall_progress = ctk.CTkProgressBar(progress_frame)
        self.overall_progress.pack(fill="x", padx=10, pady=5)
        self.overall_progress.set(0)

        self.overall_label = ctk.CTkLabel(progress_frame, text="0%")
        self.overall_label.pack()

        # Segment Progress Frame
        self.segment_frame = ctk.CTkScrollableFrame(
            self.main_frame, label_text="Segment Progress")
        self.segment_frame.pack(fill="both", expand=True)

        # Details Frame
        details_frame = ctk.CTkFrame(self.main_frame)
        details_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.status_label = ctk.CTkLabel(details_frame, text="Ready")
        self.status_label.pack()

        self.details_text = ctk.CTkTextbox(details_frame, height=100)
        self.details_text.pack(fill="both", expand=True)

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.path_entry.insert(0, config.get('default_path', ''))
        except FileNotFoundError:
            pass

    def save_config(self):
        config = {
            'default_path': self.path_entry.get()
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)

    def browse_path(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder_selected)
            self.save_config()

    def find_downloadable_files(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        self.status_label.configure(text="Analyzing URL...")
        self.file_listbox.delete("0.0", "end")
        self.window.update()

        try:
            response = requests.head(url, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()

            if 'text/html' not in content_type:
                file_name = os.path.basename(urlparse(url).path)
                self.file_listbox.insert("0.0", f"{file_name} ({url})\n")
                self.current_url = url
                self.download_button.configure(state="normal")
                self.status_label.configure(
                    text="Direct file link detected. Ready to download.")
                return

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
                        self.file_listbox.insert(
                            "end", f"{file_name} ({full_url})\n")

            if not found_files:
                self.status_label.configure(
                    text="No downloadable files found.")
            else:
                self.status_label.configure(
                    text=f"Found {len(found_files)} downloadable file(s).")
                self.current_url = found_files[0][1]
                self.download_button.configure(state="normal")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze URL: {str(e)}")
            self.status_label.configure(
                text="Error occurred while analyzing URL.")

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

        self.pause_button.configure(state="normal")
        self.cancel_button.configure(state="normal")
        self.download_button.configure(state="disabled")

        if self.auto_segment_var.get():
            segments = self.auto_segment(url)
        else:
            segments = int(self.segments_entry.get())

        self.segment_progress = [0] * segments
        self.total_downloaded = 0
        self.start_time = time.time()

        # Clear previous progress bars
        for widget in self.segment_frame.winfo_children():
            widget.destroy()

        # Create new progress bars
        self.segment_progress_bars = []
        self.segment_labels = []

        for i in range(segments):
            frame = ctk.CTkFrame(self.segment_frame)
            frame.pack(fill="x", pady=2)

            progress_bar = ctk.CTkProgressBar(frame)
            progress_bar.pack(side="left", fill="x", expand=True)
            progress_bar.set(0)
            self.segment_progress_bars.append(progress_bar)

            label = ctk.CTkLabel(frame, text=f"S{i+1}: 0%")
            label.pack(side="right", padx=5)
            self.segment_labels.append(label)

        self.download_threads = []
        for i in range(segments):
            thread = threading.Thread(
                target=self.download_segment, args=(url, save_path, i, segments))
            self.download_threads.append(thread)
            thread.start()

        self.window.after(100, self.update_ui)

    def auto_segment(self, url):
        try:
            response = requests.head(url)
            self.total_size = int(response.headers.get('content-length', 0))
            if self.total_size > 100 * 1024 * 1024:  # If file is larger than 100MB
                return 16
            elif self.total_size > 50 * 1024 * 1024:  # If file is larger than 50MB
                return 8
            else:
                return 4
        except:
            return 8

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
            overall_progress = (self.total_downloaded /
                                self.total_size) if self.total_size > 0 else 0
            self.overall_progress.set(overall_progress)
            self.overall_label.configure(text=f"{overall_progress:.1%}")

            segment_size = self.total_size // len(self.segment_progress)
            for i, (progress_bar, label) in enumerate(zip(self.segment_progress_bars, self.segment_labels)):
                segment_progress = (self.segment_progress[i] / segment_size)
                progress_bar.set(segment_progress)
                label.configure(text=f"S{i+1}: {segment_progress:.1%}")

            elapsed_time = time.time() - self.start_time
            self.download_speed = self.total_downloaded / \
                (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0

            self.update_details()

            if all(not thread.is_alive() for thread in self.download_threads):
                self.download_completed = True
                self.combine_segments()
                self.status_label.configure(text="Download completed!")
                self.pause_button.configure(state="disabled")
                self.cancel_button.configure(state="disabled")
                self.download_button.configure(state="normal")
            else:
                self.window.after(100, self.update_ui)

    def update_details(self):
        details = f"Download Speed: {self.download_speed:.2f} MB/s\n"
        details += f"Total Downloaded: {
            self.total_downloaded / (1024 * 1024):.2f} MB\n"
        details += f"Total Size: {self.total_size / (1024 * 1024):.2f} MB\n"
        details += f"Elapsed Time: {time.time() -
                                    self.start_time:.2f} seconds\n"
        details += f"Estimated Time Remaining: {
            self.estimate_time_remaining():.2f} seconds\n"

        self.details_text.delete("0.0", "end")
        self.details_text.insert("0.0", details)

    def estimate_time_remaining(self):
        if self.download_speed > 0:
            remaining_size = self.total_size - self.total_downloaded
            return remaining_size / (self.download_speed * 1024 * 1024)
        return 0

    def toggle_pause_resume(self):
        self.download_paused = not self.download_paused
        if self.download_paused:
            self.pause_button.configure(text="Resume")
            self.status_label.configure(text="Download paused")
        else:
            self.pause_button.configure(text="Pause")
            self.status_label.configure(text="Download resumed")

    def cancel_download(self):
        self.download_cancelled = True
        for thread in self.download_threads:
            thread.join()  # Wait for all threads to finish
        self.status_label.configure(text="Cancelling download...")
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
        self.overall_progress.set(0)
        self.overall_label.configure(text="0%")

        for progress_bar, label in zip(self.segment_progress_bars, self.segment_labels):
            progress_bar.set(0)
            label.configure(text="0%")

        self.details_text.delete("0.0", "end")
        self.status_label.configure(text="Download cancelled")
        self.download_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

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

        self.status_label.configure(
            text="Download completed and segments combined!")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = RapidFileDownloader()
    app.run()
