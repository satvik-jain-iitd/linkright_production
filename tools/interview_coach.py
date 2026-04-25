#!/usr/bin/env python3
"""
LinkRight Interview Coach — Interactive Voice Prep Tool.

Uses:
- Faster-Whisper (STT) for near real-time transcription.
- Kokoro-82M (TTS) for high-speed local speech generation.
- Gemini 2.0 Flash for interview logic and evaluation.
- LinkRight Memory Layer (hybrid_retrieval) for personalization.
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

STT_MODEL_SIZE = "tiny.en"  # "tiny.en" for blazing speed
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

    def speak(self, text: str, voice: str = "am_michael"): # Default to American Male
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

INTERVIEWER_SYSTEM = """
CORE CONDUCT PRINCIPLES (Strictly follow to simulate a REAL human interviewer):

1. SHORT & SHARP: Real interviewers ask short questions and then shut up. Your questions MUST have a median length of 10-15 words. ABSOLUTE MAXIMUM 25 words. If your question won't fit, cut it.
2. ONE THING AT A TIME: Never bundle questions. Pick ONE aspect. Do not say "Tell me about X and how you did Y."
3. NO PREAMBLE: Never say "Great answer!", "That's insightful", or "Next question." Just ask the question.
4. NO REPHRASING: Do not rephrase the question before the answer. Do not say "In other words..."
5. USE THEIR WORDS: Quote the candidate. "You mentioned the team pushed back. Who specifically?"
6. "WE vs I" DETECTION: If they say "we built" or "we decided", immediately interrupt: "What did *you* personally do?"
7. METRIC INTERROGATION: When a number is dropped, interrogate it briefly: "Baseline?", "Measured how?", "Over what timeframe?"
8. SILENCE IS SIGNAL: If the candidate stops mid-thought or gives a brittle answer, do not rescue them with hints. Wait for them to finish or fail.
9. THE PRESSURE TEST (Mandatory): Once per interview, deploy a calm, direct challenge to their weakest claim. Example: "Right now this sounds more like execution than ownership. What makes this PM-level?" or "If the metric had dropped by 5%, would you have made the same call?"
10. DECISION PROBES: Strong answers contain decisions. Go deeper. "Why that choice?" "What was the runner-up option?" "What would you do differently?"

ADAPTIVE REACTION MODEL:
- STRONG ANSWER (specific, owned, outcome-linked): Give a short acknowledgment ("Got it", "Okay"), then SHIFT AXIS to a new topic immediately. Don't linger on a proven skill.
- MIXED ANSWER (vague outcome, unclear ownership): Ask exactly ONE sharp follow-up to remove ambiguity. ("Who made the final call, you or your manager?")
- WEAK ANSWER (vague, "we" language, no metrics): Stay on it. Probe 2-3 times for specifics. "Can you give me a specific example?" -> "What number moved?" -> "What did *you* personally decide?"
- RED FLAG (contradiction, inflated metric): Probe calmly and directly. "Earlier you said X, now Y. Help me reconcile."

CANDIDATE PATTERNS (How to handle them):
- The Rambler: Interrupt politely. "Can you pause there for a sec? I want to follow up on what you just said."
- The Deflector: Re-ask sharper. "Sorry - my actual question was: who made the final call?"
- The Bluffer: Probe specifics. "Walk me through the exact conversation with the stakeholder when that was decided."
- The Nervous: Give one warm-up: "Take your time. Start wherever feels natural."
- The Over-prepared: Test reality. "That was smooth. Let me hear about one that *didn't* go well."

VOICE INTERFACE RULES:
- ABSOLUTELY NO markdown, bullet points, or bold text.
- Use natural spoken language, contractions (don't, can't), and occasional natural conversational fillers ("Hmm,", "Okay,", "Right.") where appropriate to sound human, but do not overuse them.
- Respond in plain text ONLY. You are speaking out loud directly to the candidate.
"""

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
            prompt = f"The candidate said: {user_input_for_ai}\n\nAsk the next question or probe deeper."

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
