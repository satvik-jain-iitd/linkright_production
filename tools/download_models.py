#!/usr/bin/env python3
import os
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent

KOKORO_ONNX_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
VOICES_BIN_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"

def download_file(url, dest):
    if dest.exists():
        print(f"✓ {dest.name} already exists.")
        return
    print(f"Downloading {dest.name} from {url}...")
    urllib.request.urlretrieve(url, dest)
    print(f"✓ {dest.name} downloaded.")

def main():
    os.makedirs(TOOLS_DIR, exist_ok=True)
    
    download_file(KOKORO_ONNX_URL, TOOLS_DIR / "kokoro-v0_19.onnx")
    download_file(VOICES_BIN_URL, TOOLS_DIR / "voices.bin")
    
    print("\nAll models ready. You can now run:")
    print("python repo/tools/interview_coach.py")

if __name__ == "__main__":
    main()
