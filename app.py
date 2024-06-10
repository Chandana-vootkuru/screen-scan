from flask import Flask, render_template, jsonify, request
from threading import Thread
import os
import time
import pygetwindow as gw
from PIL import Image, ImageGrab
from imagehash import dhash
import webview

app = Flask(__name__, static_url_path='/static')

# Global variables to control the screenshot capture process
screenshot_count = 0
capture_running = False
selected_window = None

# Function to take a full-screen screenshot
def take_full_screen_screenshot(folder, filename):
    # Check if the folder exists, create it if not
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as e:
            print(f"Error: Could not create directory '{folder}': {e}")
            return
    
    # Capture full screen
    full_screen = ImageGrab.grab()

    # Save the full-screen screenshot
    full_screen.save(os.path.join(folder, filename))

# Function to find and delete duplicate images using DCT hash
def find_and_delete_duplicates(folder, roi):
    # Check if the folder exists
    if not os.path.exists(folder):
        print(f"Error: Directory '{folder}' does not exist.")
        return 0
    
    hash_dict = {}
    duplicates_deleted = 0

    for root, dirs, files in os.walk(folder):
        for file in files:
            file_path = os.path.join(root, file)
            img = Image.open(file_path)
            img_roi = img.crop(roi)  # Crop image to ROI
            img_hash = str(dhash(img_roi))

            if img_hash in hash_dict:
                print(f"Duplicate found: {file_path}. Deleting...")
                os.remove(file_path)
                duplicates_deleted += 1
            else:
                hash_dict[img_hash] = file_path

    return duplicates_deleted

# Function to continuously capture screenshots and delete duplicates
def capture_and_delete_screenshots(folder, roi):
    global screenshot_count
    global capture_running
    global selected_window

    while capture_running:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f'Screen Scan_{timestamp}.png'

        if selected_window and selected_window.isActive and not selected_window.isMinimized:
            take_full_screen_screenshot(folder, filename)
            screenshot_count += 1
        else:
            print(f"Target application not in focus or minimized. Waiting...")

        time.sleep(15)

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html', screenshot_count=screenshot_count)

# Route to start the screenshot capture process
@app.route('/start_capture', methods=['POST'])
def start_capture():
    global capture_running
    global screenshot_count
    global selected_window
    screenshot_count = 0
    capture_running = True

    # Get selected window based on radio button choice
    window_name = request.form.get('window')
    selected_window = None
    for window in gw.getAllWindows():
        if window_name in window.title:
            selected_window = window
            break

    if not selected_window:
        return jsonify(result=f'Error: Could not find "{window_name}" first active the {window_name} then press start')

    # Start a separate thread for capturing screenshots
    capture_thread = Thread(target=capture_and_delete_screenshots, args=("Screen Scan", (0, 0, 1510, 740)))
    capture_thread.start()

    return jsonify(result=f'Capture started for window "{window_name}".')

# Route to stop the screenshot capture process
@app.route('/stop_capture', methods=['POST'])
def stop_capture():
    global capture_running

    # Stop the capture thread
    capture_running = False

    # Print a message indicating waiting for a few seconds
    print("Waiting for a few seconds before stopping capture...")

    # Wait for a few seconds to ensure the capture thread has stopped
    time.sleep(5)

    # Find and delete duplicate images
    duplicates_deleted = find_and_delete_duplicates("Screen Scan", (0, 0, 1500, 740))

    total_saved = screenshot_count - duplicates_deleted

    print(f"Total Screenshots Captured: {screenshot_count}")
    print(f"Total Duplicates Deleted: {duplicates_deleted}")
    print(f"Total Screenshots Saved: {total_saved}")

    return jsonify(result=f'Capture stopped. {total_saved} screenshots saved. {duplicates_deleted} duplicates deleted.')

def create_gui():
    # Create and run the GUI for the Flask app
    window = webview.create_window("Screen Scan", "http://127.0.0.1:5000/")
    webview.start()

if __name__ == "__main__":
    # Start the Flask app in a separate thread
    flask_thread = Thread(target=app.run, kwargs={'debug': False})
    flask_thread.daemon = True
    flask_thread.start()

    # Create and run the GUI for the Flask app
    create_gui()
