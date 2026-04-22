#!/usr/bin/env python3
"""
Lumina — Daily Affirmations · Audio Generation Script

Generates one MP3 per affirmation using Microsoft Edge TTS (free, local).

Voice: en-GB-SoniaNeural — warm, nurturing British female (same voice as
the Aha! word-builder game).

Output layout (matches the front-end):
  audio/<cat-id>/<index>.mp3   e.g.  audio/self-love/0.mp3

Run from this folder:
  python3 generate_audio.py
  python3 generate_audio.py --only self-love            # one category
  python3 generate_audio.py --skip-existing             # only missing files (default)
  python3 generate_audio.py --force                     # regenerate everything
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import edge_tts

VOICE = "en-GB-SoniaNeural"
RATE = "-8%"        # slightly slower than default — meditative pacing
PITCH = "-2Hz"      # very slight warmth
CONCURRENCY = 8     # parallel generation cap

ROOT = Path(__file__).parent
INDEX_HTML = ROOT / "index.html"
AUDIO_DIR = ROOT / "audio"


def extract_affirmations() -> dict[str, list[str]]:
    """Parse the const A = {...} block out of index.html."""
    src = INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(r"const A = (\{[\s\S]*?\n\});", src)
    if not m:
        sys.exit("Could not find `const A = {...}` block in index.html")
    block = m.group(1)

    # Convert JS object literal to JSON-compatible by replacing single quotes
    # carefully. Our data is all double-quoted strings, so it's already valid JSON.
    try:
        return json.loads(block)
    except json.JSONDecodeError as e:
        sys.exit(f"Could not parse affirmations as JSON: {e}")


async def synth(text: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(str(out_path))


async def run(args):
    data = extract_affirmations()
    if args.only:
        if args.only not in data:
            sys.exit(f"No category '{args.only}'. Known: {', '.join(data)}")
        data = {args.only: data[args.only]}

    jobs = []
    for cat_id, items in data.items():
        for i, text in enumerate(items):
            out = AUDIO_DIR / cat_id / f"{i}.mp3"
            if out.exists() and not args.force:
                continue
            jobs.append((cat_id, i, text, out))

    total = sum(len(v) for v in data.values())
    todo = len(jobs)
    print(f"Voice: {VOICE}  rate={RATE}  pitch={PITCH}")
    print(f"Categories: {len(data)}  Total clips: {total}  To generate: {todo}")
    if not jobs:
        print("Nothing to do. Use --force to regenerate everything.")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0

    async def worker(job):
        nonlocal done
        cat_id, idx, text, out = job
        async with sem:
            try:
                await synth(text, out)
                done += 1
                if done % 20 == 0 or done == todo:
                    print(f"  [{done:>4}/{todo}]  {cat_id}/{idx}.mp3")
            except Exception as e:
                print(f"  FAIL  {cat_id}/{idx}: {e}", file=sys.stderr)

    await asyncio.gather(*(worker(j) for j in jobs))
    print("Done.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="Generate only this category id")
    ap.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
