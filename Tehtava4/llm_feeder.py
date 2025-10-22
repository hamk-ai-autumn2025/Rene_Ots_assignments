#!/usr/bin/env python3
"""Command-line utility to send multiple content sources to an LLM."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


@dataclass
class SourceContent:
    label: str
    text: str


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate text from local files or URLs and query an LLM. "
            "Supported sources: text, CSV, DOCX, PDF, and web pages."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more paths or URLs to include as context.",
    )
    parser.add_argument(
        "-q",
        "--query",
        help="Custom user prompt. Defaults to requesting a summary.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional path to write the LLM response. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model identifier (default: %(default)s).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=12000,
        help=(
            "Maximum characters from each source to send to the LLM. "
            "Allows controlling prompt size while retaining context (default: %(default)s)."
        ),
    )
    return parser.parse_args(argv)


def load_sources(inputs: Iterable[str], max_chars: int) -> List[SourceContent]:
    sources: List[SourceContent] = []
    for raw in inputs:
        if raw.startswith(("http://", "https://")):
            text = load_url(raw)
            label = raw
        else:
            path = Path(raw).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(f"Input not found: {raw}")
            text = load_file(path)
            label = str(path)

        text = normalize_text(text)
        if max_chars and len(text) > max_chars:
            text = text[:max_chars]
        if not text.strip():
            raise ValueError(f"No textual content extracted from {raw}")

        sources.append(SourceContent(label=label, text=text))
    return sources


def load_url(url: str) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - import guard
        missing = "requests and beautifulsoup4"
        raise RuntimeError(f"Fetching URLs requires installing {missing}") from exc

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def load_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".rst"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".csv":
        return read_csv(path)
    if suffix in {".docx"}:
        return read_docx(path)
    if suffix in {".pdf"}:
        return read_pdf(path)
    # Fallback to binary-safe text read, ignoring errors.
    return path.read_text(encoding="utf-8", errors="ignore")


def read_csv(path: Path) -> str:
    rows: List[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            rows.append(", ".join(cell.strip() for cell in row))
    return "\n".join(rows)


def read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("Reading DOCX files requires installing python-docx") from exc

    document = Document(path)
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)


def read_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("Reading PDF files requires installing PyPDF2") from exc

    reader = PdfReader(path)
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        header = f"[Page {index}]"
        pages.append(f"{header}\n{text.strip()}")
    return "\n\n".join(pages)


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    compact = "\n".join(line for line in lines if line)
    return compact


def build_prompt(query: str | None, sources: Sequence[SourceContent]) -> str:
    instruction = query or "Summarize the following sources. Highlight key points and common themes."
    context_parts = []
    for idx, source in enumerate(sources, start=1):
        context_parts.append(f"Source {idx}: {source.label}\n{source.text}")
    context = "\n\n---\n\n".join(context_parts)
    return f"{instruction}\n\nContext:\n{context}"


def call_llm(prompt: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("This tool requires the openai package. Install it with 'pip install openai'.") from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set the OPENAI_API_KEY environment variable to use this tool.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that works with curated multi-source context."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    choice = response.choices[0]
    content = choice.message.content if choice.message else ""
    if not content:
        raise RuntimeError("LLM returned an empty response.")
    return content.strip()


def write_output(text: str, output_path: str | None) -> None:
    if output_path:
        path = Path(output_path).expanduser().resolve()
        path.write_text(text, encoding="utf-8")
    else:
        print(text)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        sources = load_sources(args.inputs, args.max_chars)
        prompt = build_prompt(args.query, sources)
        response_text = call_llm(prompt, args.model)
        write_output(response_text, args.output)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
