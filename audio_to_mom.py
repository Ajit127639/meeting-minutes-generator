import whisper
from transformers import pipeline

# ---------- 1. LOAD WHISPER MODEL ----------
print("Loading Whisper model...")
stt_model = whisper.load_model("base")

# ---------- 2. AUDIO TO TEXT ----------
print("Transcribing audio...")
stt_result = stt_model.transcribe(
    "sample3.mp3",          # audio file
    language="en",          # change to "hi" for Hindi
    temperature=0           # stable output
)

transcript = stt_result["text"]

print("\n----- TRANSCRIPT -----\n")
print(transcript)

# ---------- 3. LOAD SUMMARIZATION MODEL ----------
print("\nLoading summarization model...")
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn"
)

# ---------- 4. GENERATE SUMMARY ----------
summary = summarizer(
    transcript,
    max_length=120,
    min_length=40,
    do_sample=False
)[0]["summary_text"]

# ---------- 5. SIMPLE NLP FOR DECISIONS & ACTIONS ----------
decisions = []
actions = []

sentences = transcript.split(".")

for s in sentences:
    s = s.strip()
    lower = s.lower()

    if "decided" in lower or "agreed" in lower:
        decisions.append(s)

    if "will" in lower or "responsible" in lower or "assigned" in lower:
        actions.append(s)

# ---------- 6. FINAL MOM OUTPUT ----------
print("\n===== MINUTES OF MEETING =====\n")

print("🔹 SUMMARY:")
print(summary)

print("\n🔹 DECISIONS:")
if decisions:
    for d in decisions:
        print("-", d)
else:
    print("No explicit decisions found.")

print("\n🔹 ACTION ITEMS:")
if actions:
    for a in actions:
        print("-", a)
else:
    print("No action items found.")
