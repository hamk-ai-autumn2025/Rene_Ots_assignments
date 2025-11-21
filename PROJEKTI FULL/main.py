import os
from io import BytesIO

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    send_from_directory,
)
from fpdf import FPDF
from openai import OpenAI, APIError

load_dotenv()

app = Flask(__name__)
_client = None

LENGTH_OPTIONS = {
    "short": {
        "prompt": "a short story of about 3 playful paragraphs",
        "max_tokens": 350,
        "label": "Short (≈3 paragraphs)",
    },
    "medium": {
        "prompt": "a medium-length story of about 5 paragraphs",
        "max_tokens": 550,
        "label": "Medium (≈5 paragraphs)",
    },
    "long": {
        "prompt": "a longer tale of 7+ paragraphs with rich detail",
        "max_tokens": 750,
        "label": "Long (≈7+ paragraphs)",
    },
}
DEFAULT_LENGTH = "medium"


def get_client() -> OpenAI:
    """Create a single OpenAI client instance using the env var API key."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Please add your API key as an environment variable."
        )

    _client = OpenAI(api_key=api_key)
    return _client


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/character-images/<path:filename>")
def character_images(filename: str):
    """Serve character artwork stored in the Images folder."""
    return send_from_directory("Images", filename)


@app.post("/generate")
def generate_story():
    data = request.get_json(force=True)
    character = data.get("character", "princess")
    setting = data.get("setting", "castle")
    genre = data.get("genre", "adventure")
    tone = data.get("tone", "funny")
    length_key = data.get("length", DEFAULT_LENGTH)
    length_config = LENGTH_OPTIONS.get(length_key, LENGTH_OPTIONS[DEFAULT_LENGTH])

    prompt = (
        "You are an imaginative children's storyteller. "
        f"Write {length_config['prompt']} for kids aged 5-7. "
        "Use simple, cheerful language and weave in sensory details. "
        f"Main character: {character}. "
        f"Setting: {setting}. "
        f"Genre: {genre}. "
        f"Tone: {tone}. "
        "Close the story with a feel-good ending that hints at more adventures."
    )

    try:
        client = get_client()
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You craft delightful, imaginative stories for young kids.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=length_config["max_tokens"],
        )

        story = completion.choices[0].message.content.strip()
        return jsonify({"story": story, "lengthLabel": length_config["label"]})
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except APIError as exc:
        return jsonify({"error": exc.message}), 500
    except Exception as exc:  # pragma: no cover - just in case
        return jsonify({"error": str(exc)}), 500


def _pdf_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")


def _apply_simple_theme(pdf: FPDF) -> None:
    """Fill the page with a light gradient-like background."""
    pdf.set_fill_color(244, 237, 255)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_fill_color(229, 214, 255)
    pdf.rect(0, 0, 210, 90, "F")


@app.post("/download")
def download_pdf():
    data = request.get_json(force=True)
    story = data.get("story", "").strip()
    if not story:
        return jsonify({"error": "Story text is required to create a PDF."}), 400

    details = data.get("details", {})
    details = data.get("details", {})
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _apply_simple_theme(pdf)

    pdf.set_text_color(70, 34, 120)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 14, _pdf_text("AI Kids Story"), ln=True)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _pdf_text("Made with imagination just for you!"), ln=True)
    pdf.ln(6)

    pdf.set_text_color(50, 28, 95)
    pdf.set_font("Helvetica", "B", 13)
    meta_pairs = [
        ("Main Character", details.get("character")),
        ("Setting", details.get("setting")),
        ("Genre", details.get("genre")),
        ("Tone", details.get("tone")),
        ("Story Length", details.get("lengthLabel")),
    ]

    for label, value in meta_pairs:
        if value:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                0,
                8,
                _pdf_text(f"{label}: {value}"),
                border=0,
                fill=True,
            )
            pdf.ln(1)

    pdf.ln(4)
    pdf.set_text_color(90, 45, 140)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _pdf_text("Your Story"), ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(60, 28, 110)
    pdf.set_fill_color(255, 255, 255)
    for paragraph in story.split("\n"):
        text = paragraph.strip()
        if text:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 7.5, _pdf_text(text), border=0, fill=True)
            pdf.ln(1.5)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="ai-kids-story.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
