import datetime
import os
import sys
import webbrowser

import openai
import speech_recognition as sr
import win32com.client

from config import apikey

speaker = win32com.client.Dispatch("SAPI.SpVoice")
speaker.Voice = speaker.GetVoices().Item(1)
speaker.Speak("Hi Anish, I'm Friday")

chatStr = ""

def friday():
    global chatStr
    openai.api_key = apikey
    chatStr += "Friday: "
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=chatStr,
        temperature=0.7,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        # stop=["\n"]
    )


def chat(query):
    global chatStr

    openai.api_key = apikey
    chatStr += f"Anish: {query}\n Friday: "
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=chatStr,
        temperature=0.7,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # todo: Wrap this inside of a  try catch block
    speaker.Speak(response["choices"][0]["text"])
    chatStr += f"{response['choices'][0]['text']}\n"
    print(chatStr)
    return response["choices"][0]["text"]


def ai(prompt):
    openai.api_key = apikey
    text = f"OpenAI response for Prompt: {prompt} \n *************************\n\n"
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.7,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # todo: Wrap this inside of a  try catch block
    # print(response["choices"][0]["text"])
    text += response["choices"][0]["text"]
    if not os.path.exists("Openai"):
        os.mkdir("Openai")

    # with open(f"Openai/prompt- {random.randint(1, 2343434356)}", "w") as f:
    with open(f"Openai/{''.join(prompt.split('intelligence')[1:]).strip()}.txt", "w") as f:
        f.write(text)





def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        # r.pause_threshold =  0.5
        audio = r.listen(source)
        try:
            print("Recognizing...")
            query = r.recognize_google(audio, language="en-uk")
            print(f"User said: {query}")
            return query
        except Exception as e:
            return "Some Error Occurred. Sorry from Friday"


while 1:
    speaker.Speak("Listening...")
    query = takeCommand()
    # todo: add more sites
    sites = [["youtube", "https://www.youtube.com"], ["wikipedia", "https://www.wikipedia.com"],
             ["google", "https://www.google.com"], ["netflix", "https://netflix.com"],
             ["instagram", "https://instagram.com"], ["amazon", "https://www.amazon.in"],
             ["spotify", "https://www.spotify.com"]]
    for site in sites:
        if f"Open {site[0]}".lower() in query.lower():
            speaker.Speak(f"Opening {site[0]} sir...")
            webbrowser.open(site[1])

    # todo : add specific song
    if "open music".lower() in query:
        musicPath = "C:\\Users\\anish\\Music\\MP3.mp3"
        speaker.Speak(f"Opening music sir...")
        os.system(musicPath)

    elif "the time" in query:
        strfTime = datetime.datetime.now().strftime("%H:%M:%S")
        speaker.Speak(f"Sir the time is {strfTime}")
    # write a program to tell weather of current location
    elif "weather" in query:
        speaker.Speak("Tell me the city name sir")
        cityName = takeCommand()
        url = f"https://wttr.in/{cityName}?format=3"

    elif "open autocad".lower() in query.lower():
        speaker.Speak("Opening Autocad sir...")
        os.system("C:\\Program Files\\AutoCAD\\acad.exe")

    elif "Using Artificial Intelligence".lower() in query.lower():
        ai(prompt=query)

    elif "exit".lower() in query.lower() or "quit".lower() in query.lower() or "bye".lower() in query.lower():
        speaker.Speak("Bye Anish, See you soon from Friday")
        sys.exit()

    elif "reset chat".lower() in query.lower():
        chatStr = ""
        speaker.Speak("Chat reseted sir")

    else:
        chat(query)
