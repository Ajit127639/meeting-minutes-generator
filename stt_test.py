import whisper
import os

print("Current folder:", os.getcwd())

model = whisper.load_model("base")

result = model.transcribe(
    "sample.mp3",
    language="en",
    task="transcribe",
    temperature=0
)
#result = model.transcribe("sample.mp3")

print("\n----- TRANSCRIPT -----\n")
print(result["text"])