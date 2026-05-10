from transformers import pipeline

# ---------- INPUT TRANSCRIPT ----------
transcript = """
Good morning everyone. Today we discussed the project timeline.
The team agreed that the backend module will be completed by next week.
Ajit will work on the NLP module.
The final review meeting will be held on Friday.
"""

# ---------- LOAD SUMMARIZATION MODEL ----------
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn"
)

# ---------- SUMMARY ----------
summary = summarizer(
    transcript,
    max_length=120,
    min_length=40,
    do_sample=False
)[0]["summary_text"]

# ---------- SIMPLE RULE-BASED EXTRACTION ----------
decisions = []
actions = []

sentences = transcript.split(".")

for s in sentences:
    s = s.strip()
    if "agreed" in s.lower() or "decided" in s.lower():
        decisions.append(s)
    if "will" in s.lower() or "responsible" in s.lower():
        actions.append(s)

# ---------- OUTPUT ----------
print("\n===== MEETING MINUTES =====\n")

print("🔹 SUMMARY:")
print(summary)

print("\n🔹 DECISIONS:")
for d in decisions:
    print("-", d)

print("\n🔹 ACTION ITEMS:")
for a in actions:
    print("-", a)
