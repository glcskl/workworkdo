#!/usr/bin/env python3
"""With a given probability, append a row to data/history.csv.

Purpose: each daily run may or may not produce a push, creating a natural
(not uniform, not fully green) contribution graph while every produced commit
carries real dashboard data.
USAGE: update_history.py <probability-0-1> "<commit-message>"
"""
import csv
import os
import random
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "history.csv")


def main():
    prob = float(sys.argv[1])
    message = sys.argv[2] if len(sys.argv) > 2 else "chore(radar): update"
    rnd = random.Random()
    rnd.seed(f"{datetime.now(timezone.utc).date().isoformat()}:{os.getenv('RUN_ID', 'x')}")
    if rnd.random() > prob:
        print(f"skip (roll {rnd.random():.2f} > p={prob:.2f})")
        return 0

    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    write_header = not os.path.exists(PATH) or os.path.getsize(PATH) == 0
    with open(PATH, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp", "message"])
        w.writerow([datetime.now(timezone.utc).isoformat(), message])
    print(f"recorded entry: {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
