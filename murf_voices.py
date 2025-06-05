from murf import Murf

client = Murf(
    api_key="ap2_84e1322d-f5b6-4ba4-ab7f-9933a8508c71",
)
voices = client.text_to_speech.get_voices()
print(voices)
