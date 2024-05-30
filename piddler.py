import requests
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

def download_segment(url, start, end, temp_file_name, username, password, segment_pbar):
    headers = {'Range': f'bytes={start}-{end}'}
    response = requests.get(url, headers=headers, stream=True, auth=(username, password))
    bytes_downloaded = 0
    with open(temp_file_name, 'rb+') as f:
        f.seek(start)
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                bytes_downloaded += len(chunk)
                segment_pbar.update(len(chunk))
    return bytes_downloaded

def download_file(url, segment_count=1, username=None, password=None):
    # Determine file name from URL
    file_name = url.split('/')[-1]
    
    # Create a temporary file to store downloaded segments
    temp_file_name = f'{file_name}.part'
    with open(temp_file_name, 'wb') as f:
        f.seek(segment_count * 1024**2 - 1)
        f.write(b'\0')
    
    # Get file size
    file_size = int(requests.head(url).headers.get('content-length', 0))
    
    # Calculate segment size
    segment_size = file_size // segment_count
    
    # Create a list to store segment ranges
    ranges = [(i*segment_size, min((i+1)*segment_size-1, file_size-1)) for i in range(segment_count)]
    
    # Download segments in parallel
    with ThreadPoolExecutor(max_workers=segment_count) as executor:
        segment_pbars = [tqdm(total=(end - start + 1), desc=f"Segment {i}", unit="B", unit_scale=True, leave=False) for i, (start, end) in enumerate(ranges)]
        futures = []
        for i, (start, end) in enumerate(ranges):
            futures.append(executor.submit(download_segment, url, start, end, temp_file_name, username, password, segment_pbars[i]))
        
        # Track progress for each segment
        bytes_downloaded = 0
        for future in futures:
            bytes_downloaded += future.result()
        
        # Close progress bars
        for pbar in segment_pbars:
            pbar.close()
    
    # Merge segments into final file
    with open(file_name, 'wb') as f:
        for i in range(segment_count):
            with open(temp_file_name, f'rb') as part:
                part.seek(i*segment_size)
                f.write(part.read(segment_size))
    
    # Remove temporary file
    os.remove(temp_file_name)
    
    print(f'Download completed: {file_name}')

# Example usage
url = input("Enter URL: ")
segment_count = int(input("Enter segment count: "))

# Check if URL is FTP
if url.startswith("ftp://"):
    username = input("Enter FTP username: ")
    password = input("Enter FTP password: ")
else:
    username = None
    password = None

download_file(url, segment_count, username, password)

