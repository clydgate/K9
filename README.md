# K9
Robotic dog project
Chris Lydgate. Portland, Oregon. 2021.

Overview
K9 is a robot inspired by the robotic dog from the 1980s Doctor Who series. The chassis was borrowed from a broken robotic vacuum from Goodwill. The brains consist of a Raspberry Pi Zero connected to a Google AIY Voice bonnet. AIY allows K9 to take advantage of some impressive Google technology, including voice assistant, speech recognition, text-to-speech, and more. There’s also an Adafruit motorshield to deal with the motors and servos. Program is written in python.

VOICE COMMAND
K9 is designed to respond to voice commands. Our main() loop invokes the google AIY cloud-speech magic. This waits for an utterance, then sends the utterance to the cloud and returns a text object. It’s very strong. K9 inspects the object, attempts to match it to a list of things it knows how do to, and proceeds accordingly. For example, we can check the time, check the weather, look up stuff in Wikipedia, tell jokes, etc. It uses a basic text-to-speech package (not as nice as Alexa, but oh well). We can also physically move the robot—go forward, go back, etc. Eventually would like to control robot arm.

IMPLEMENTED SO FAR
•	Voice command. TTS. Basic motor control. Hotword.
•	TIME
•	WEATHER. Get weather for Portland (how can we figure out where we are?)
•	JOKES. 
•	WIKIPEDIA. Doesn’t always work right, but it does often work OK

KNOWN ISSUES
•	long latency at startup, possibly because Pi has to launch python?
•	slight lag before it begins to listen. Also not sure how long it waits for user before bailing on that cycle. 

NOTE
This code was designed for a particular hardware configuration by an amateur hacker who doesn't actually know how to code in python (or anything else). The code abounds with hacks, bugs, and kludges. For entertainment purposes only!
