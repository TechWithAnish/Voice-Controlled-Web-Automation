#!/usr/bin/env python3
"""
Test script for speech recognition functionality.
Use this to verify your microphone and speech recognition setup.
"""

import speech_recognition as sr
import pyttsx3
import time

def test_microphone():
    """Test microphone availability and functionality."""
    print("🎤 Testing microphone...")
    
    try:
        # List available microphones
        mic_list = sr.Microphone.list_microphone_names()
        print(f"📋 Available microphones ({len(mic_list)}):")
        for i, microphone_name in enumerate(mic_list):
            print(f"  {i}: {microphone_name}")
        
        # Test default microphone
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("\n🔧 Adjusting for ambient noise... Please wait.")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Microphone test completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False

def test_speech_recognition():
    """Test speech recognition functionality."""
    print("\n🗣️ Testing speech recognition...")
    
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("🎤 Say something (you have 10 seconds)...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            
        print("🔄 Processing speech...")
        text = recognizer.recognize_google(audio, language="en-US")
        print(f"✅ Speech recognized: '{text}'")
        return True, text
        
    except sr.WaitTimeoutError:
        print("⏰ No speech detected within timeout period.")
        return False, None
    except sr.UnknownValueError:
        print("❓ Could not understand the speech.")
        return False, None
    except sr.RequestError as e:
        print(f"❌ Speech recognition service error: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Speech recognition test failed: {e}")
        return False, None

def test_text_to_speech():
    """Test text-to-speech functionality."""
    print("\n🔊 Testing text-to-speech...")
    
    try:
        engine = pyttsx3.init()
        
        # Get available voices
        voices = engine.getProperty('voices')
        print(f"📋 Available voices ({len(voices) if voices else 0}):")
        if voices:
            for i, voice in enumerate(voices[:3]):  # Show first 3 voices
                print(f"  {i}: {voice.name} ({voice.id})")
        
        # Test speech
        test_message = "Hello! Text to speech is working correctly."
        print(f"🔊 Speaking: '{test_message}'")
        engine.say(test_message)
        engine.runAndWait()
        
        print("✅ Text-to-speech test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Text-to-speech test failed: {e}")
        return False

def run_all_tests():
    """Run all audio tests."""
    print("=" * 50)
    print("🧪 VOICE AUTOMATION AUDIO TESTS")
    print("=" * 50)
    
    # Test microphone
    mic_ok = test_microphone()
    
    # Test text-to-speech
    tts_ok = test_text_to_speech()
    
    # Test speech recognition
    if mic_ok:
        speech_ok, recognized_text = test_speech_recognition()
    else:
        speech_ok = False
        recognized_text = None
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"🎤 Microphone: {'✅ PASS' if mic_ok else '❌ FAIL'}")
    print(f"🔊 Text-to-Speech: {'✅ PASS' if tts_ok else '❌ FAIL'}")
    print(f"🗣️ Speech Recognition: {'✅ PASS' if speech_ok else '❌ FAIL'}")
    
    if recognized_text:
        print(f"📝 Last recognized text: '{recognized_text}'")
    
    if mic_ok and tts_ok and speech_ok:
        print("\n🎉 All tests passed! Your system is ready for voice automation.")
    else:
        print("\n⚠️ Some tests failed. Please check your audio setup:")
        if not mic_ok:
            print("  - Check microphone connection and permissions")
        if not tts_ok:
            print("  - Check audio output and TTS engine installation")
        if not speech_ok:
            print("  - Check internet connection for Google Speech API")

if __name__ == "__main__":
    run_all_tests()