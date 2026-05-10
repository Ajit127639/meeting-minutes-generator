import os
import io
import threading
import re
import textwrap
import sqlite3

from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, send_file

import whisper

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# ================= APP =================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            platform TEXT,
            organizer TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= MODELS =================

stt_model = None

# ================= GLOBAL STATE =================

PROGRESS = 0
RESULT = {}

# ================= HELPERS =================

def clean_sentences(text):
    sentences = re.split(r'[.\n]', text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]

def extract_agenda(text):
    agenda = []

    for s in clean_sentences(text):
        if any(k in s.lower() for k in ["agenda", "topic", "discussion", "purpose"]):
            agenda.append(s)

    return agenda or ["General discussion and updates"]

def extract_decisions(text):
    decisions = []

    patterns = [
        r"deadline will be .*",
        r"deadline is .*",
        r"final .*",
        r"confirmed .*",
        r"approved .*"
    ]

    for s in clean_sentences(text):
        for p in patterns:
            if re.search(p, s.lower()):
                decisions.append(s)
                break

    return decisions or ["No explicit decisions were finalized"]

def extract_actions(text):
    actions = []

    patterns = [
        r"[A-Z][a-z]+ is looking at .*",
        r"[A-Z][a-z]+ will work on .*",
        r"frontend .* by [A-Z][a-z]+",
        r"backend .* by [A-Z][a-z]+",
        r"handled by [A-Z][a-z]+"
    ]

    for s in clean_sentences(text):
        for p in patterns:
            if re.search(p.lower(), s.lower()):
                actions.append(s)
                break

    return actions or ["No concrete action items were assigned"]

def speakerwise_transcript(text):
    speakers = {}
    current_speaker = "Speaker 1"

    for s in clean_sentences(text):

        match = re.search(r"(my name is|i am)\s+([A-Z][a-z]+)", s, re.I)

        if match:
            current_speaker = match.group(2)

            if current_speaker not in speakers:
                speakers[current_speaker] = []

        if current_speaker not in speakers:
            speakers[current_speaker] = []

        speakers[current_speaker].append(s)

    return speakers

# ================= AUDIO PROCESS =================

def process_audio(path, meta):

    global PROGRESS
    global RESULT
    global stt_model

    if stt_model is None:
        stt_model = whisper.load_model("tiny")

    PROGRESS = 10

    transcription = stt_model.transcribe(path, fp16=False)

    transcript = transcription["text"]

    PROGRESS = 60

    # SIMPLE SUMMARY
    summary = transcript[:1000]

    PROGRESS = 85

    RESULT = {
        "meta": meta,
        "agenda": extract_agenda(transcript),
        "summary": summary,
        "decisions": extract_decisions(transcript),
        "actions": extract_actions(transcript),
        "transcript": transcript,
        "speakerwise": speakerwise_transcript(transcript)
    }

    # SAVE HISTORY

    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO history (title, date, platform, organizer, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        meta.get("title"),
        meta.get("date"),
        meta.get("platform"),
        meta.get("organizer"),
        datetime.now().strftime("%d-%m-%Y %H:%M")
    ))

    conn.commit()
    conn.close()

    PROGRESS = 100

# ================= ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/history")
def history():

    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM history ORDER BY id DESC")

    rows = cur.fetchall()

    conn.close()

    return render_template("history.html", history=rows)

@app.route("/delete_history/<int:hid>", methods=["POST"])
def delete_history(hid):

    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM history WHERE id = ?", (hid,))

    conn.commit()
    conn.close()

    return redirect("/history")

@app.route("/process", methods=["POST"])
def process():

    global PROGRESS

    PROGRESS = 0

    audio = request.files["audio"]

    path = os.path.join(UPLOAD_FOLDER, audio.filename)

    audio.save(path)

    meta = {
        "title": request.form.get("title"),
        "date": request.form.get("date"),
        "time": request.form.get("time"),
        "platform": request.form.get("platform"),
        "organizer": request.form.get("organizer"),
        "next_meeting": {
            "date": request.form.get("next_date"),
            "time": request.form.get("next_time"),
            "agenda": request.form.get("next_agenda")
        }
    }

    threading.Thread(
        target=process_audio,
        args=(path, meta)
    ).start()

    return render_template("progress.html")

@app.route("/progress")
def progress():
    return jsonify({"progress": PROGRESS})

@app.route("/result")
def result():

    if PROGRESS < 100:
        return redirect("/")

    return render_template("result.html", data=RESULT)

# ================= PDF =================

@app.route("/download")
def download():

    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    x = 50
    y = height - 50

    def heading(txt):
        nonlocal y

        c.setFont("Helvetica-Bold", 14)

        c.drawString(x, y, txt)

        y -= 22

    def wrapped(txt):
        nonlocal y

        c.setFont("Helvetica", 11)

        for line in textwrap.wrap(txt, 95):

            c.drawString(x + 10, y, line)

            y -= 16

            if y < 50:
                c.showPage()
                y = height - 50

    def bullet(txt):
        wrapped("• " + txt)

    c.setFont("Helvetica-Bold", 18)

    c.drawCentredString(width / 2, y, "MINUTES OF MEETING")

    y -= 35

    meta = RESULT["meta"]

    heading("Meeting Details")

    wrapped(f"Title: {meta['title']}")
    wrapped(f"Date: {meta['date']}")
    wrapped(f"Time: {meta['time']}")
    wrapped(f"Platform: {meta['platform']}")
    wrapped(f"Organizer: {meta['organizer']}")

    y -= 10

    heading("Discussion Summary")

    for s in RESULT["summary"].split("."):

        if len(s.strip()) > 20:
            bullet(s.strip())

    y -= 10

    heading("Decisions Taken")

    for d in RESULT["decisions"]:
        bullet(d)

    y -= 10

    heading("Action Items")

    for a in RESULT["actions"]:
        bullet(a)

    y -= 10

    heading("Speaker-wise Transcript")

    for speaker, lines in RESULT["speakerwise"].items():

        wrapped(f"{speaker}:")

        for l in lines:
            bullet(l)

    y -= 20

    c.setFont("Helvetica-Oblique", 9)

    c.drawString(
        x,
        y,
        "Generated using AI-based Automated Meeting Minutes Generator"
    )

    c.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Meeting_Minutes.pdf",
        mimetype="application/pdf"
    )

# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )