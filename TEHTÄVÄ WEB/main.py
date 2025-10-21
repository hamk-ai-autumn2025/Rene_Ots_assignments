#!/usr/bin/env python3

import argparse
import os
import sys
import time
import pathlib
import base64
from openai import OpenAI

ASPECT_TO_SIZE = {
    "1:1":   "1024x1024",
    "16:9":  "1792x1024",
    "4:3":   "1792x1024",
    "3:4":   "1024x1792",
    "9:16":  "1024x1792",
}

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate images via OpenAI")
    p.add_argument("prompt", help="Main image description (prompt)")
    p.add_argument("-r", "--ratio", choices=list(ASPECT_TO_SIZE.keys()), default="1:1")
    p.add_argument("-c", "--count", type=int, default=1)
    p.add_argument("-q", "--quality", choices=["low", "medium", "high", "auto"], default="high")
    return p.parse_args()

def main():
    args = parse_args()

    if args.count < 1 or args.count > 8:
        print("Count must be between 1 and 8.", file=sys.stderr)
        sys.exit(1)

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("Missing OPENAI_API_KEY environment variable.", file=sys.stderr)
        sys.exit(2)

    client = OpenAI(api_key=key)
    size = ASPECT_TO_SIZE[args.ratio]

    try:
        resp = client.images.generate(
            model="gpt-image-1",
            prompt=args.prompt.strip(),
            size=size,
            quality=args.quality,
            n=args.count,
        )
        items = list(getattr(resp, "data", []) or [])
        if not items:
            raise RuntimeError("Empty response data")
    except Exception as e:
        print(f"OpenAI request failed: {e}", file=sys.stderr)
        sys.exit(3)

    ts = time.strftime("%Y%m%d_%H%M%S")
    prefix = f"ai_image_{args.ratio.replace(':','x')}_{ts}"

    out_paths = []

    for i, item in enumerate(items, start=1):
        filename = f"{prefix}_{i:02d}.png"
        path = pathlib.Path.cwd() / filename
        b64 = getattr(item, "b64_json", None) or getattr(item, "b64", None) or getattr(item, "image", None)
        if not b64:
            continue
        try:
            data_bytes = base64.b64decode(b64)
            path.write_bytes(data_bytes)
            out_paths.append(path)
        except Exception:
            continue

    for p in out_paths:
        print(str(p))

if __name__ == "__main__":
    main()