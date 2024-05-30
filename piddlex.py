import requests
import ftplib
import os
import time
import re
from tqdm import tqdm
from urllib.parse import urlparse


def download_file(url, num_segments=5, username=None, password=None, resume=False):
    """Downloads a file from HTTP(S) or FTP with segmented downloading and resume support."""
    start_time = time.time()

    # Parse URL to extract components
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    filename = os.path.basename(parsed_url.path)

    # Extract username and password if provided in the URL
    if not username:
        username = parsed_url.username
    if not password:
        password = parsed_url.password
    
    if url.startswith("ftp://"):
        ftp = ftplib.FTP(host)
        ftp.login(username, password)
        file_size = ftp.size(parsed_url.path)
    else:
        with requests.head(url, stream=True) as r:
            file_size = int(r.headers.get("content-length", 0))

    if not file_size:
        print("Could not determine file size or file does not exist.")
        return

    # Segment size calculation (with rounding)
    segment_size = -(-file_size // num_segments)
    downloaded_size = 0
    
    # Resume support: check if file exists and determine starting point
    if resume and os.path.exists(filename):
        downloaded_size = os.path.getsize(filename)
        start_byte = downloaded_size
    else:
        start_byte = 0
    
    # Download loop with progress bar
    with tqdm(total=file_size, unit="B", unit_scale=True, desc=filename, initial=downloaded_size) as pbar:
        for i in range(num_segments):
            end_byte = min(start_byte + segment_size, file_size) - 1  # Calculate end byte

            if start_byte >= file_size:
                break  # Download complete

            headers = {"Range": f"bytes={start_byte}-{end_byte}"} if url.startswith("http") else {}
            if url.startswith("ftp://"):
                with open(filename, "ab" if resume else "wb") as f:
                    ftp.retrbinary(f"RETR {parsed_url.path}", f.write, rest=start_byte)
            else:
                with requests.get(url, headers=headers, stream=True) as r:
                    for chunk in r.iter_content(chunk_size=8192):  # 8 KB chunks
                        if chunk:
                            with open(filename, "ab" if resume else "wb") as f:
                                f.write(chunk)
                                pbar.update(len(chunk))
                            downloaded_size += len(chunk)

            start_byte += segment_size  # Move to next segment

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

