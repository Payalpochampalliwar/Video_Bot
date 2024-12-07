import os
import asyncio
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tqdm import tqdm
import time

# Global Constants
TOKEN = "flic_0e2f63d99f1f210734f65a1c2268675ab9ddde054fd9d6c81fcb5409d8ccf15c"  # Replace with your actual token
VIDEO_DIR = "videos/"    # Directory to monitor for new videos

#API functions
def get_upload_url(token):
    """
    Fetch a pre-signed upload URL from the server.
    Parameters:
        token (str): Authentication token for API access.
    Returns:
        dict: JSON response containing upload URL and hash, or None if an error occurs.
    """
    url = "https://api.socialverseapp.com/posts/generate-upload-url"
    headers = {
        "Flic-Token": token,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching upload URL: {e}")
        return None

def upload_video(file_path, pre_signed_url):
    """
    Upload a video file to the server using the pre-signed URL.
    Parameters:
        file_path (str): Path to the video file.
        pre_signed_url (str): Pre-signed URL for uploading the file.
    Returns:
        bool: True if upload succeeds, False otherwise.
    """
    try:
        with open(file_path, "rb") as file:
            file_size = os.path.getsize(file_path)
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="Uploading") as pbar:
                response = requests.put(pre_signed_url, data=file, stream=True)
                response.raise_for_status()
                pbar.update(file_size)
        print(f"Uploaded {file_path} successfully.")
        return True
    except requests.RequestException as e:
        print(f"Error uploading video {file_path}: {e}")
        return False

def create_post(token, title, hash_id, category_id=25):
    """
    Create a post entry in the server after uploading the video.
    Parameters:
        token (str): Authentication token.
        title (str): Title of the post.
        hash_id (str): Hash ID returned after video upload.
        category_id (int): Category ID for the post (default is 1).
    Returns:
        bool: True if post creation succeeds, False otherwise.
    """
    url = "https://api.socialverseapp.com/posts"
    headers = {
        "Flic-Token": token,
        "Content-Type": "application/json"
    }
    data = {
        "title": title,
        "hash": hash_id,
        "is_available_in_public_feed": False,
        "category_id": category_id
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Post created with title: {title}")
        return True
    except requests.RequestException as e:
        print(f"Error creating post: {e}")
        return False
    
def process_existing_videos():
    """
    Processes all existing .mp4 files in the video directory at startup.
    """
    for filename in os.listdir(VIDEO_DIR):
        if filename.endswith(".mp4"):
            file_path = os.path.join(VIDEO_DIR, filename)
            print(f"Processing existing file: {file_path}")
            process_video(file_path)


# Directory Monitoring Class
class VideoHandler(FileSystemEventHandler):
    """
    Handles events for new files added to the monitored directory.
    """
    def on_created(self, event):
        print(f"Event detected: {event.src_path}")
        if event.is_directory:
           return
        if event.src_path.endswith(".mp4"):
           print(f"New video detected: {event.src_path}")
        (process_video(event.src_path))

# Async Task for Video Upload and Post Creation
async def process_video(file_path):
    """
    Process a video: Get upload URL, upload video, and create post.
    Parameters:
        file_path (str): Path to the video file.
    """
    print(f"Processing {file_path}...")
    upload_data = get_upload_url(TOKEN)
    if not upload_data:
        print("Failed to fetch upload URL.")
        return

    pre_signed_url = upload_data["url"]
    hash_id = upload_data["hash"]

    upload_success = upload_video(file_path, pre_signed_url)
    if not upload_success:
        print("Failed to upload video.")
        return

    post_success = create_post(TOKEN, os.path.basename(file_path), hash_id)
    if post_success:
        os.remove(file_path)  # Delete the local file after successful upload
        print(f"Video {file_path} processed and uploaded successfully!")




# Main Function
async def main():
    """
    Main function to initialize directory monitoring and keep the program running.
    """
    # Ensure the videos directory exists
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR)

    # Set up directory monitoring
    observer = Observer()
    event_handler = VideoHandler()
    observer.schedule(event_handler, path=VIDEO_DIR, recursive=False)
    observer.start()

    try:
        print(f"Monitoring directory: {VIDEO_DIR}. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Monitoring service has been stopped.")
    except KeyboardInterrupt:
        print("\nStopped monitoring.")

if __name__ == "__main__":
        # Process existing files in the directory
    process_existing_videos()
    asyncio.run(main())