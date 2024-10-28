# Rapid File Downloader Documentation

## Overview

The Rapid File Downloader is a multi-threaded download manager built with customtkinter (a modern version of Tkinter). It enables fast file downloading by segmenting files and downloading each segment in parallel, which optimizes download speed.

## Key Features

- **Segmented Downloading:** Divides files into multiple segments, downloading each in parallel to accelerate the process.
- **Auto Segmentation:** Automatically determines the number of segments based on file size.
- **Pause/Resume Functionality:** Enables pausing and resuming of downloads.
- **Multi-threaded Downloads:** Each segment is downloaded in a separate thread, maximizing bandwidth utilization.
- **File Merging:** Once downloading is complete, segments are combined into a single file.

## Core Concepts

### 1. Segmented Downloading

The core idea behind segmented downloading is to split files into smaller chunks, downloading each chunk simultaneously. Each segment is downloaded independently by specifying byte ranges, which allows for parallel downloading.

#### Logic

Files are split into segments based on the following calculation:

```python
segment_size = self.total_size // total_segments
```

Each segment download request uses an HTTP Range header to specify the byte range:

```python
headers = {'Range': f'bytes={start}-{end}'}
response = requests.get(url, headers=headers, stream=True)
```

This parallel downloading optimizes network usage by retrieving multiple segments simultaneously.

### 2. Auto Segment Calculation

The Rapid File Downloader calculates the number of segments based on the file's total size:

- Files larger than 100 MB: 16 segments
- Files between 50 MB and 100 MB: 8 segments
- Files smaller than 50 MB: 4 segments

```python
if self.total_size > 100 * 1024 * 1024:
    return 16
elif self.total_size > 50 * 1024 * 1024:
    return 8
else:
    return 4
```

### 3. Threaded Download

Each segment is downloaded in a separate thread, ensuring parallel processing that significantly speeds up downloads.

#### Logic

The downloader creates a thread for each segment:

```python
for i in range(segments):
    thread = threading.Thread(
        target=self.download_segment, args=(url, save_path, i, segments))
    self.download_threads.append(thread)
    thread.start()
```

Each thread downloads a specific byte range and writes data to a part file:

```python
response = requests.get(url, headers=headers, stream=True)
with open(file_name, 'wb') as file:
    for data in response.iter_content(chunk_size=1024):
        file.write(data)
```

### 4. Combining Segments

Once all segments are downloaded, they are combined into a single file in sequential order.

#### Logic

After downloading, the segments are merged:

```python
with open(file_name, 'wb') as output_file:
    for i in range(len(self.segment_progress)):
        segment_file = f"{file_name}.part{i}"
        with open(segment_file, 'rb') as segment:
            output_file.write(segment.read())
        os.remove(segment_file)
```

### 5. Pause/Resume Download

The Rapid File Downloader includes a pause/resume function, allowing users to control downloads as needed.

#### Logic

To pause, a `self.download_paused` flag is set, which causes threads to wait:

```python
while self.download_paused:
    time.sleep(0.1)
```

Resuming resets the flag, allowing threads to continue:

```python
if self.download_paused:
    self.pause_button.configure(text="Resume")
    self.status_label.configure(text="Download paused")
else:
    self.pause_button.configure(text="Pause")
    self.status_label.configure(text="Download resumed")
```

### 6. Dynamic Progress Updates

The user interface displays real-time progress for each segment and the total download progress.

#### Logic

Overall progress is calculated and updated every 100 ms:

```python
overall_progress = (self.total_downloaded / self.total_size)
self.overall_progress.set(overall_progress)
self.overall_label.configure(text=f"{overall_progress:.1%}")
```

Each segment's progress is updated similarly:

```python
segment_progress = (self.segment_progress[i] / segment_size)
progress_bar.set(segment_progress)
label.configure(text=f"S{i+1}: {segment_progress:.1%}")
```

### 7. Speed Calculation and Time Estimation

The downloader calculates download speed and estimates remaining time.

#### Logic

Speed is calculated based on downloaded bytes and elapsed time:

```python
self.download_speed = self.total_downloaded / (1024 * 1024 * elapsed_time)
```

Estimated time remaining is derived from remaining file size and current download speed:

```python
remaining_size = self.total_size - self.total_downloaded
return remaining_size / (self.download_speed * 1024 * 1024)
```

## How Download Speed is Increased

1. **Parallel Downloads:** Splitting files into parts and downloading each part in parallel maximizes network bandwidth usage, achieving faster downloads.
2. **Multi-threading:** Each segment is handled by its own thread, allowing concurrent processing to boost download speeds.
3. **Auto Segmentation:** Files are divided into more segments as size increases, optimizing download speeds for larger files.

## Conclusion

The Rapid File Downloader leverages parallel downloads and multi-threading to provide high-speed downloads. By segmenting files, fetching segments simultaneously, and merging them post-download, this downloader maximizes efficiency and performance.
