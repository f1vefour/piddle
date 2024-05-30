import requests
import ftplib
import os
import time
import concurrent.futures
from tqdm import tqdm
from urllib.parse import urlparse
import math


def download_segment(url, filename, start_byte, end_byte, username=None, password=None, progress_bar=None):
    """Downloads a segment of the file and updates the progress bar."""
    if url.startswith("ftp://"):
        mode = "wb" if start_byte == 0 else "ab"  # Write mode: 'wb' for new or 'ab' for append
        with ftplib.FTP(urlparse(url).hostname) as ftp:
            ftp.login(username, password)
            with open(filename, mode) as f:
                ftp.retrbinary(f"RETR {urlparse(url).path}", 
                               lambda data: (f.write(data), progress_bar.update(len(data))) if progress_bar else f.write(data),
                               rest=start_byte)
    else:
        headers = {"Range": f"bytes={start_byte}-{end_byte}"}
        with requests.get(url, headers=headers, stream=True) as r:
            with open(filename, "ab") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))


def download_file(url, num_segments=5, username=None, password=None, resume=False):
    """Downloads a file with segmented downloading, resume support, and accurate progress updates."""
    start_time = time.time()

    # Parse URL to extract components
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    filename = os.path.basename(parsed_url.path) or "downloaded_file"  # Use 'downloaded_file' if filename is empty

    # Extract username and password if provided in the URL
    if not username:
        username = parsed_url.username
    if not password:
        password = parsed_url.password
    
    if url.startswith("ftp://"):
        with ftplib.FTP(host) as ftp:
            ftp.login(username, password)
            file_size = ftp.size(parsed_url.path)
    else:
        try:
            with requests.head(url, allow_redirects=True) as r:  # Handle redirects for HTTP(S)
                r.raise_for_status()
                file_size = int(r.headers.get("content-length", 0))
        except requests.exceptions.RequestException as e:
            print(f"Error getting file size: {e}")
            return

    if not file_size:
        print("Could not determine file size or file does not exist.")
        return

    # Segment size calculation (with rounding)
    segment_size = -(-file_size // num_segments)
    downloaded_size = 0
    
    # Resume support: check if file exists and determine starting point
    if resume and os.path.exists(filename):
        downloaded_size = os.path.getsize(filename)
        # Adjust the number of segments if resuming and file is partially downloaded
        if downloaded_size < file_size:
            num_segments = math.ceil((file_size - downloaded_size) / segment_size)
    else:
        downloaded_size = 0

    # Download loop with progress bar and concurrent segment downloads
    with tqdm(total=file_size, unit="B", unit_scale=True, desc=filename, initial=downloaded_size) as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_segments) as executor:
            futures = []
            start_byte = downloaded_size
            for i in range(num_segments):
                end_byte = min(start_byte + segment_size - 1, file_size - 1)
                if start_byte >= file_size:
                    break
                futures.append(executor.submit(
                    download_segment, url, filename, start_byte, end_byte, username, password, pbar
                ))  # Pass the progress bar to the download_segment function
                start_byte += segment_size
    
            concurrent.futures.wait(futures)  # Wait for all downloads to complete

        # Calculate and print download speed
        end_time = time.time()
        download_time = end_time - start_time
        if download_time > 0:
            download_speed = downloaded_size / download_time
            print(f"Download speed: {download_speed:.2f} B/s")


if __name__ == "__main__":
    url = input("Enter URL to download (HTTP/HTTPS/FTP): ")
    num_segments = int(input("Enter number of segments for parallel downloading: "))
    resume = input("Resume download? (y/n): ").lower() == "y"

    if url.startswith("ftp://"):
        username = input("Enter FTP username (if applicable): ")
        password = input("Enter FTP password (if applicable): ")
    else:
        username, password = None, None

    download_file(url, num_segments, username, password, resume)

