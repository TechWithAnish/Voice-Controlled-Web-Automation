import speech_recognition as sr
print(sr.Microphone.list_microphone_names())

recognizer = sr.Recognizer()
with sr.Microphone(device_index=2) as source:
    print("Say something...")
    recognizer.pause_threshold = 1
    try:
        audio = recognizer.listen(source, timeout=5)
        print("Recognizing...")
        query = recognizer.recognize_google(audio, language="en-in")
        print(f"You said: {query}")
    except sr.UnknownValueError:
        print("Could not understand audio.")
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
    except Exception as e:
        print(f"Error: {e}")