from app.voice.stt import SpeechToText


stt = SpeechToText()

text = stt.listen_and_transcribe(
    seconds=5
)

print()
print("================================")
print("YOU SAID:")
print(text)
print("================================")