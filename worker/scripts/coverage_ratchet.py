#!/usr/bin/env python3
"""Coverage ratchet — ensures test coverage never decreases.

Reads coverage.xml (pytest-cov output), compares against stored minimum
in worker/.coverage-minimum. Fails if coverage dropped, auto-updates
the minimum when coverage increases.

Usage:
    pytest tests/ --cov=app/tools --cov-report=xml:coverage.xml
    python scripts/coverage_ratchet.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

COVERAGE_XML = Path(__file__).parent.parent / "coverage.xml"
MINIMUM_FILE = Path(__file__).parent.parent / ".coverage-minimum"


def get_current_coverage() -> float:
    if not COVERAGE_XML.exists():
        print(f"ERROR: {COVERAGE_XML} not found. Run pytest with --cov-report=xml first.")
        sys.exit(1)
    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()
    line_rate = float(root.attrib.get("line-rate", "0"))
    return round(line_rate * 100, 2)


def get_stored_minimum() -> float:
    if not MINIMUM_FILE.exists():
        return 0.0
    return float(MINIMUM_FILE.read_text().strip())


def main():
    current = get_current_coverage()
    minimum = get_stored_minimum()

    print(f"Current coverage: {current}%")
    print(f"Stored minimum:   {minimum}%")

    if current < minimum:
        print(f"\nFAILED: Coverage dropped from {minimum}% to {current}%")
        print("Fix: add tests to restore coverage before merging.")
        sys.exit(1)

    if current > minimum:
        MINIMUM_FILE.write_text(f"{current}\n")
        print(f"\nRatcheted up: {minimum}% → {current}%")
    else:
        print("\nCoverage unchanged — OK")


if __name__ == "__main__":
    main()
