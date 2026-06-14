import sys
import os
import subprocess

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if __name__ == "__main__":
    app_path = resource_path("main.py")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.headless", "true",
        "--server.port", "8501",
        "--browser.serverAddress", "localhost"
    ])