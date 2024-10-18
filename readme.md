# IDM Documentation

## Overview

The ModernParallelIDM is a multi-threaded download manager built with customtkinter (a modern version of Tkinter). It allows downloading files in segments to increase download speed by utilizing multiple threads.

## Key Features

- **Segmented Downloading:** Breaks files into multiple segments and downloads each segment in parallel to speed up the process.
- **Auto Segmentation:** Automatically decides the number of segments based on the file size.
- **Pause/Resume Functionality:** Allows the user to pause and resume the download.
- **Multi-threaded Downloads:** Each segment is downloaded in a separate thread, maximizing network bandwidth utilization.
- **File Merging:** After download completion, the segments are combined into a single file.

## Core Concepts

### 1. Segmented Downloading

The idea is to split the file into smaller chunks and download them simultaneously using multiple threads. The file is divided into ranges of bytes, and each range is downloaded independently.

#### Logic

The file is split based on the number of segments, calculated as:

```python
segment_size = self.total_size // total_segments
```

Each segment is downloaded with a Range HTTP header. This header specifies the start and end byte for the request:

```python
headers = {'Range': f'bytes={start}-{end}'}
response = requests.get(url, headers=headers, stream=True)
```

This makes each segment an independent download, allowing multiple segments to be fetched in parallel, utilizing the full bandwidth of the network.

### 2. Auto Segment Calculation

The app automatically decides the number of segments based on the total size of the file. Large files are split into more segments.

#### Logic

- For files larger than 100 MB, 16 segments are used.
- For files larger than 50 MB but less than 100 MB, 8 segments are used.
- For files smaller than 50 MB, 4 segments are used.

```python
if self.total_size > 100 * 1024 * 1024:
    return 16
elif self.total_size > 50 * 1024 * 1024:
    return 8
else:
    return 4
```

### 3. Threaded Download

Each segment download is handled in a separate thread. This ensures that all the segments are downloaded in parallel, significantly speeding up the download process.

#### Logic

The code creates a thread for each segment:

```python
for i in range(segments):
    thread = threading.Thread(
        target=self.download_segment, args=(url, save_path, i, segments))
    self.download_threads.append(thread)
    thread.start()
```

Each thread downloads a specific byte range (defined by start and end) and writes the data into a part file:

```python
response = requests.get(url, headers=headers, stream=True)
with open(file_name, 'wb') as file:
    for data in response.iter_content(chunk_size=1024):
        file.write(data)
```

### 4. Combining Segments

After all segments are downloaded, the part files are combined into a single file. Each segment file is opened and its contents are written into the final output file in sequence.

#### Logic

Once all the segments are downloaded, the files are combined into one:

```python
with open(file_name, 'wb') as output_file:
    for i in range(len(self.segment_progress)):
        segment_file = f"{file_name}.part{i}"
        with open(segment_file, 'rb') as segment:
            output_file.write(segment.read())
        os.remove(segment_file)
```

### 5. Pause/Resume Download

The download process can be paused and resumed. When paused, the threads wait until resumed.

#### Logic

Pausing happens by setting a flag `self.download_paused` to `True`, which causes the threads to wait:

```python
while self.download_paused:
    time.sleep(0.1)
```

Resuming resets the flag and the threads continue downloading:

```python
if self.download_paused:
    self.pause_button.configure(text="Resume")
    self.status_label.configure(text="Download paused")
else:
    self.pause_button.configure(text="Pause")
    self.status_label.configure(text="Download resumed")
```

### 6. Dynamic Progress Updates

The UI shows real-time progress for both individual segments and the overall download. This is achieved by continuously updating the progress bars based on the downloaded bytes.

#### Logic

The progress is calculated as the ratio of downloaded bytes to the total file size and updated every 100 ms:

```python
overall_progress = (self.total_downloaded / self.total_size)
self.overall_progress.set(overall_progress)
self.overall_label.configure(text=f"{overall_progress:.1%}")
```

Each segment's progress is also updated similarly:

```python
segment_progress = (self.segment_progress[i] / segment_size)
progress_bar.set(segment_progress)
label.configure(text=f"S{i+1}: {segment_progress:.1%}")
```

### 7. Speed Calculation and Time Estimation

The download speed is calculated based on the amount of data downloaded and the elapsed time. The remaining time is estimated using this speed.

#### Logic

Download speed is calculated by dividing the total downloaded bytes by the elapsed time:

```python
self.download_speed = self.total_downloaded / (1024 * 1024 * elapsed_time)
```

The estimated time remaining is calculated by dividing the remaining file size by the current download speed:

```python
remaining_size = self.total_size - self.total_downloaded
return remaining_size / (self.download_speed * 1024 * 1024)
```

## How Download Speed is Increased

1. **Parallel Downloads:** By splitting the file into multiple parts and downloading them in parallel, the network bandwidth is better utilized. Instead of downloading sequentially, all segments are fetched at the same time, leading to faster overall download times.

2. **Multi-threading:** Each segment is downloaded in its own thread, so multiple threads work concurrently. This increases the download speed, especially on high-speed connections or when downloading large files.

3. **Auto Segmentation:** Large files are automatically divided into more segments, allowing the application to make the most out of the available bandwidth. This is especially useful for big downloads, as they are split into more parts for parallel downloading.

## Conclusion

This download manager enhances download speed using parallel downloads and multi-threading. By breaking files into smaller parts, fetching them simultaneously, and combining them at the end, the overall download process becomes much faster.
