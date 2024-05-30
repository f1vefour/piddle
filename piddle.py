import os
import requests
import ftplib
from urllib.parse import urlparse
import threading
from tqdm import tqdm

def download_http_https(url, dest, start, end, pbar):
    headers = {'Range': f'bytes={start}-{end}'}
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        with open(dest, 'r+b') as f:
            f.seek(start)
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    except requests.RequestException as e:
        print(f"Error downloading {url}: {e}")

def download_ftp(url, dest, start, end, pbar, username, password):
    parsed_url = urlparse(url)
    ftp = ftplib.FTP(parsed_url.hostname)
    
    try:
        ftp.login(username, password)
        print(f"Logged in to FTP server {parsed_url.hostname}")
        ftp.cwd(os.path.dirname(parsed_url.path))
        print(f"Changed directory to {os.path.dirname(parsed_url.path)}")
        
        with open(dest, 'r+b') as f:
            def callback(data):
                nonlocal start
                f.seek(start)
                f.write(data)
                pbar.update(len(data))
                start += len(data)
                if start > end:
                    return
        
            ftp.retrbinary(f"RETR {os.path.basename(parsed_url.path)}", callback, rest=start)
        ftp.quit()
    except ftplib.error_perm as e:
        print(f"FTP permission error: {e}")
    except FileNotFoundError as e:
        print(f"Local file error: {e}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def download_segment(url, dest, start, end, pbar, username=None, password=None):
    parsed_url = urlparse(url)
    
    if parsed_url.scheme in ['http', 'https']:
        download_http_https(url, dest, start, end, pbar)
    elif parsed_url.scheme == 'ftp':
        download_ftp(url, dest, start, end, pbar, username, password)
    else:
        print(f"URL scheme {parsed_url.scheme} is not supported.")

def main():
    url = input("Enter the URL to download: ").strip()
    thread_count = int(input("Enter the number of threads: ").strip())
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    
    if parsed_url.scheme in ['http', 'https']:
        response = requests.head(url)
        total_size = int(response.headers.get('content-length', 0))
        username = password = None
    elif parsed_url.scheme == 'ftp':
        username = input("Enter FTP username: ").strip()
        password = input("Enter FTP password: ").strip()
        ftp = ftplib.FTP(parsed_url.hostname)
        ftp.login(username, password)
        ftp.cwd(os.path.dirname(parsed_url.path))
        total_size = ftp.size(parsed_url.path)
        ftp.quit()
    else:
        print(f"URL scheme {parsed_url.scheme} is not supported.")
        return
    
    part_size = total_size // thread_count

    with open(file_name, 'wb') as f:
        f.truncate(total_size)

    pbar = tqdm(total=total_size, unit='iB', unit_scale=True, unit_divisor=1024)

    threads = []
    for i in range(thread_count):
        start = i * part_size
        end = start + part_size - 1 if i < thread_count - 1 else total_size - 1
        thread = threading.Thread(target=download_segment, args=(url, file_name, start, end, pbar, username, password))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    pbar.close()
    print(f"Downloaded {url} to {file_name}")

if __name__ == "__main__":
    main()

