# LLM Feeder CLI

`llm_feeder.py` is a command-line tool that extracts text from multiple sources (local files or URLs) and submits the aggregated context to an OpenAI chat model. It supports plain text, CSV, DOCX, and PDF files as well as HTML pages.

## Prerequisites

- Python 3.10+
- Dependencies listed in `requirements.txt`
- An OpenAI API key exposed as `OPENAI_API_KEY`

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python llm_feeder.py <inputs...> [options]
```

Examples:

- Summarize a report and a supporting web page (default behaviour):
  ```bash
  python llm_feeder.py docs/report.pdf https://example.com/article
  ```

- Ask a custom question and save the result:
  ```bash
  python llm_feeder.py notes.txt data.csv --query "Extract action items" --output actions.md
  ```

- Limit the context sent to the LLM:
  ```bash
  python llm_feeder.py meeting.docx --max-chars 6000
  ```

## Options

- `--query`, `-q` – Custom prompt. Defaults to summarisation.
- `--output`, `-o` – File path for saving the response. Prints to stdout otherwise.
- `--model` – OpenAI chat model ID. Defaults to `gpt-4o-mini`.
- `--max-chars` – Maximum characters per source to include in the prompt (default: 12000).

## Notes

- URLs require `requests` and `beautifulsoup4`.
- DOCX files require `python-docx`.
- PDF files require `PyPDF2`.
- The tool trims excessive whitespace and truncates sources beyond the `--max-chars` limit to stay within model context windows.
