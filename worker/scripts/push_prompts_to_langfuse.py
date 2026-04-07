"""One-time script to push all prompts to Langfuse registry.

Usage: LANGFUSE_SECRET_KEY=... LANGFUSE_PUBLIC_KEY=... python -m scripts.push_prompts_to_langfuse
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langfuse import Langfuse

from app.tools.nugget_extractor import _SYSTEM_PROMPT as NUGGET_PROMPT
from app.pipeline.prompts import (
    PHASE_1_2_SYSTEM,
    PHASE_4A_VERBOSE_SYSTEM,
    PHASE_4C_CONDENSE_SYSTEM,
    PHASE_5_BATCHED_SYSTEM,
)

PROMPTS = {
    "nugget_extractor": NUGGET_PROMPT,
    "phase_1_2": PHASE_1_2_SYSTEM,
    "phase_4a_verbose": PHASE_4A_VERBOSE_SYSTEM,
    "phase_4c_condense": PHASE_4C_CONDENSE_SYSTEM,
    "phase_5_width": PHASE_5_BATCHED_SYSTEM,
}

def main():
    lf = Langfuse()
    for name, prompt_text in PROMPTS.items():
        try:
            lf.create_prompt(
                name=name,
                prompt=prompt_text,
                labels=["production"],
                type="text",
            )
            print(f"Pushed: {name}")
        except Exception as e:
            print(f"Failed: {name} -- {e}")
    lf.flush()
    print("Done.")

if __name__ == "__main__":
    main()
