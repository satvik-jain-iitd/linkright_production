#!/usr/bin/env python3
"""
LinkRight Interview Coach — Interactive Voice Prep Tool.

Uses:
- Faster-Whisper (STT) for near real-time transcription.
- Kokoro-82M (TTS) for high-speed local speech generation.
- Gemini 2.0 Flash for interview logic and evaluation.
- LinkRight Memory Layer (hybrid_retrieval) for personalization.

Setup:
1. pip install faster-whisper kokoro-onnx sounddevice soundfile numpy httpx pydantic supabase python-dotenv
2. Download kokoro-v0_19.onnx and voices.bin (or use the helper below).
3. Ensure .env has SUPABASE_URL, SUPABASE_SERVICE_KEY, and GEMINI_API_KEY.
"""

import os
import sys
import asyncio
import json
import logging
import time
import queue
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Add repo root to path so we can import worker modules
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))

from worker.app.tools.hybrid_retrieval import hybrid_retrieve, NuggetResult
from worker.app.llm.gemini import GeminiProvider
from worker.app.db import create_supabase

# Load environment variables
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "worker" / ".env")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("InterviewCoach")

# ---------------------------------------------------------------------------
# Models & Configuration
# ---------------------------------------------------------------------------

STT_MODEL_SIZE = "base.en"  # "tiny.en", "base.en", "small.en", "distil-large-v3"
TTS_MODEL_PATH = REPO_ROOT / "tools" / "kokoro-v0_19.onnx"
TTS_VOICES_PATH = REPO_ROOT / "tools" / "voices.bin"
SAMPLE_RATE = 16000

# ---------------------------------------------------------------------------
# TTS: Kokoro-82M
# ---------------------------------------------------------------------------

class TTSManager:
    def __init__(self):
        self.kokoro = None
        try:
            from kokoro_onnx import Kokoro
            if TTS_MODEL_PATH.exists() and TTS_VOICES_PATH.exists():
                self.kokoro = Kokoro(str(TTS_MODEL_PATH), str(TTS_VOICES_PATH))
                logger.info("✓ Kokoro TTS initialized")
            else:
                logger.warning("! Kokoro weights not found at repo/tools/. Voice will be disabled.")
        except ImportError:
            logger.warning("! kokoro-onnx not installed. Voice will be disabled.")

    def speak(self, text: str, voice: str = "af_heart"):
        if not self.kokoro:
            print(f"\nAI: {text}")
            return

        print(f"\nAI (speaking...): {text}")
        samples, sample_rate = self.kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
        sd.play(samples, sample_rate)
        sd.wait()

# ---------------------------------------------------------------------------
# STT: Faster-Whisper
# ---------------------------------------------------------------------------

class STTManager:
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(STT_MODEL_SIZE, device="cpu", compute_type="int8")
            logger.info(f"✓ Faster-Whisper ({STT_MODEL_SIZE}) initialized")
        except ImportError:
            logger.error("! faster-whisper not installed. Run: pip install faster-whisper")
            sys.exit(1)

    def transcribe(self, audio_path: str) -> str:
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        text = "".join([s.text for s in segments]).strip()
        return text

# ---------------------------------------------------------------------------
# Audio Recording
# ---------------------------------------------------------------------------

def record_audio(filename: str):
    q = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    print("\n[Press Enter to START recording, then Enter to STOP]")
    input()
    
    with sf.SoundFile(filename, mode='x', samplerate=SAMPLE_RATE, channels=1) as file:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
            print("Recording... (Speak now)")
            
            # Start a thread to wait for the second Enter press
            stop_event = threading.Event()
            def wait_for_stop():
                input()
                stop_event.set()
            
            t = threading.Thread(target=wait_for_stop, daemon=True)
            t.start()
            
            while not stop_event.is_set():
                file.write(q.get())
                
    print("Recording stopped.")

# ---------------------------------------------------------------------------
# Interview Coach Logic
# ---------------------------------------------------------------------------

INTERVIEWER_SYSTEM = """You are a senior hiring manager conducting a realistic interview.
Your goal is to test the candidate's skills and their ability to articulate their past achievements.

CONTEXT:
1. The target Job Description (JD) is provided.
2. The candidate's "Career Nuggets" (their real memory layer) are provided.

RULES:
- Be professional but firm.
- Use the STAR method (Situation, Task, Action, Result) to evaluate their answers.
- If they miss a quantified result, ask them to provide one.
- Reference their actual nuggets if they are being vague. e.g. "You mentioned in your profile that you improved customer happiness at Sprinklr. Can you tell me more about the 'voice-of-customer' loops you used there?"
- Keep your responses concise (2-4 sentences max) to maintain the flow.
- After feedback, ask exactly one follow-up question or a new behavioral question.

OUTPUT:
Respond in plain text. You are speaking directly to the candidate."""

async def main():
    print("=== LinkRight Interview Coach (Voice) ===")
    
    # 1. Setup
    sb = create_supabase()
    gemini = GeminiProvider(
        api_key=os.environ.get("GEMINI_API_KEY", ""),
        api_keys=[os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 4)]
    )
    tts = TTSManager()
    stt = STTManager()

    # 2. Get Context
    user_id = input("\nEnter User ID (UUID): ").strip()
    jd_path = input("Path to JD file (or press Enter to paste text): ").strip()
    
    if jd_path and Path(jd_path).exists():
        jd_text = Path(jd_path).read_text()
    else:
        print("Paste JD text here (then Ctrl-D or Ctrl-Z and Enter):")
        jd_text = sys.stdin.read().strip()

    if not jd_text:
        print("Error: No JD provided.")
        return

    # 3. Retrieve Memory Layer
    print("\nRetrieving your career highlights from the memory layer...")
    nuggets, _ = await hybrid_retrieve(sb, user_id, jd_text, limit=10)
    
    nuggets_context = "\n".join([
        f"- [{n.importance}] {n.answer} (Company: {n.company})"
        for n in nuggets
    ])
    
    print(f"Loaded {len(nuggets)} relevant nuggets.")

    # 4. Start Interview Loop
    chat_history = [
        {"role": "user", "content": f"Hi, I'm ready for the interview for this JD:\n{jd_text}\n\nMy achievements:\n{nuggets_context}"}
    ]

    while True:
        # AI Generates Question/Response
        user_input_for_ai = chat_history[-1]["content"] if chat_history[-1]["role"] == "user" else ""
        
        # If it's the very first message, we need a different prompt
        if len(chat_history) == 1:
            prompt = "Start the interview. Introduce yourself and ask the first behavioral question based on the JD."
        else:
            prompt = f"The candidate said: {user_input_for_ai}\n\nProvide feedback on their STAR method and ask the next question."

        response = await gemini.complete(
            system=INTERVIEWER_SYSTEM,
            user=prompt,
            temperature=0.7
        )
        
        ai_text = response.text
        chat_history.append({"role": "assistant", "content": ai_text})
        
        # TTS Speaks
        tts.speak(ai_text)

        # Record User Answer
        audio_file = "temp_answer.wav"
        if os.path.exists(audio_file): os.remove(audio_file)
        
        record_audio(audio_file)
        
        # STT Transcribes
        print("Transcribing...")
        user_answer = stt.transcribe(audio_file)
        print(f"You: {user_answer}")
        
        if not user_answer or user_answer.lower() in ["quit", "exit", "stop"]:
            print("Interview ended. Good luck!")
            break
            
        chat_history.append({"role": "user", "content": user_answer})

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
