#!/usr/bin/env python3

"""
K9 is a roving robot that can respond to voice commands.
Makes heavy use of google aiy voice library
Hardware:
    Raspberry Pi Zero
    Google AIY Voice Bonnet
    Adafruit Motor bonnet connected to an old robot vacuum chassis
Major libraries:
    aiy,board
    aiy.voice
    wikipedia
    pygame (this is for playing the "blip" sound)
"""
import argparse
import locale
import logging
from datetime import datetime

from aiy.board import Board, Led
from aiy.pins import PIN_A, PIN_B
from aiy.cloudspeech import CloudSpeechClient   # does the speech-recognition magic
import aiy.voice.tts    # does the text-to-speech
import wikipedia        # you can guess. this module actually doesn't work very well.
import requests
import json
import time
from adafruit_motorkit import MotorKit  # this runs the motor interface
kit = MotorKit()    # feels weird to init this here, but can't figure out where else to do it
motor_speed = 0.4   # this is default speed for motors. 1.0 is max. 
FORWARD = -1    
BACKWARD = 1
motor_direction = FORWARD
from pygame import mixer    #this is the soundfile player
from pickle import NONE     #not sure why this is here; do we even use it?
"""
Now declare some global variables. I don't like doing this here but where else?
"""
user_name = "Norbert"   # define global variable for user's name
user_name_tries = 0     # keep track of how many times we've tred to set name
awake_flag = 0          # user has to wake us up by uttering hotword
awake_time = 0          # remember when we woke up
bed_time = 5            # this is how long K9 stays awake 
k9_volume = 20      # sets initial volume. user can tell k9 to get louder/quieter
wiki_sentences = 5 # sets how many sentences to read from wikipedia.
k9_board = Board()  # again, i hate that we have to do this here instead of in an init func
mixer.init()    #set up the soundfile player
"""
This func makes K9 say something using the AIY tts module. Here's where we set pitch, accent etc
"""
def say(text):  #set up K9 voice options like accent, speed, pitch
    aiy.voice.tts.say(text, lang='en-GB', volume=k9_volume, pitch=120, speed=100, device='default')
    return 1
def locale_language():  #honestly don't understand how this works exactly
    language, _ = locale.getdefaultlocale()
    return language
def wake_up(text=""):   # this is invoked when user utters the hotword.
    global awake_time
    global awake_flag
    awake_time = time.time()
    awake_flag = 1
    say("Yes, "+ user_name + ". Your wish is my command.")
    return
"""
next define actions k9 will take in response to various commands. these functions all
take a text argument, which is the phrase the user uttered to launch the command.
most of the time we don't actually do anything with this phrase, but there are a
few where it's important. Also note that some of them rely on user_name. I wish we could
define them after setting up the phrase_bank, but we can't. First we will define functions
that help user control K9 hardware--LEDs, motors. And set global variables like speed and user_name
"""
def light_on(text=""):
    global k9_board
    k9_board.led.state = Led.ON
    return 
def light_off(text=""):
    global k9_board
    k9_board.led.state = Led.OFF
    return 
def light_blink(text=""):
    global k9_board
    k9_board.led.state = Led.BLINK
    return 
def light_pulse(text=""):
    global k9_board
    k9_board.led.state = Led.PULSE_SLOW
    return
def get_louder(text=""):
    global k9_volume
    k9_volume = k9_volume + 10
    say("Affirmative")
    return 
def get_quieter(text=""):
    global k9_volume
    k9_volume = k9_volume - 10
    if k9_volume <= 0 :
        k9_volume = 5
    say("Affirmative")
    return
def speed_up(text=""):
    global motor_speed
    motor_speed = motor_speed + 0.2
    if (motor_speed > 1) :
        motor_speed = 1
        say("Thats my top speed.")
    return
def slow_down(text=""):
    global motor_speed 
    motor_speed = motor_speed - 0.2
    if motor_speed <= 0 :
        motor_speed = 0
        say("I have slowed to a stop.")
    return
"""
Now some funcs to move K9 around. we have already initialized the motor objects that are connected to the
motorshield. once you set the throttle, the motor starts moving at that speed and returns. in an ideal world, we would 
implement a state machine or something. but for now we'll just do this for arbitrary duration.
"""
def turn_right(text=""):
    start_time = time.time()
    kit.motor1.throttle = -0.5
    kit.motor2.throttle = 0.5
    say("turning right")
    while time.time() - start_time < 0.25:  # this executes roughly a quarter turn.
        pass
    kit.motor1.throttle = None
    kit.motor2.throttle = None
    return
def turn_left(text=""):
    start_time = time.time()
    kit.motor1.throttle = 0.5
    kit.motor2.throttle = -0.5
    say("turning left")
    while time.time() - start_time < 0.25:  # this executes roughly a quarter turn.
        pass
    kit.motor1.throttle = None
    kit.motor2.throttle = None
    return
def attack(text=""):
    say("attack!")
    go_forward("go forward 5")
    return
def go_forward(text=""):
    global motor_direction
    motor_direction = FORWARD
    engage_motor(text)
    return
def go_back(text=""):
    global motor_direction
    motor_direction = BACKWARD
    engage_motor(text)
    return
"""
engage_motor() is where we actually make the damn thing go back or forward. Note this is one of
the cases where we actually want to read the text object, because it may contain useful info,
such "go forward 7" or "go back 3". Of course if they just say "go forward" then we use a default
value for the duration. There must be prettier ways to do all this but oh well.
"""
def engage_motor(text=""):
    word_list = text.split()
    try :
        third_word = word_list[2] #get the third word
    except :
        third_word = "3"    # there wasn't one. so set to 3 seconds
    try :
        throttle_duration = int(third_word)
    except :
        throttle_duration = 3.0 # if int() didn't work, set for 3 seconds
    if throttle_duration > 10 :
        throttle_duration = 10  # let's set a default max so user can't ask for 1 million seconds 
    start_time = time.time()
    kit.motor1.throttle = motor_direction*motor_speed
    kit.motor2.throttle = motor_direction*motor_speed        
    while time.time() - start_time < throttle_duration:
        pass    # in theory this is where we could look at sensors to avoid obstacles.
    kit.motor1.throttle = None
    kit.motor2.throttle = None
    return
"""
don't think we actually need this func any more
"""
def halt(text=""):    
    global motor_direction
    global motor_speed
    kit.motor1.throttle = None
    kit.motor2.throttle = None
    motor_direction = FORWARD
    motor_speed = 0.3
    return
def spin(text=""):  # spin around clockwise for 4 seconds.
    start_time = time.time()
    kit.motor1.throttle = 0.75
    kit.motor2.throttle = -0.75
    say("and around we go")
    while time.time() - start_time < 4:
        pass
    kit.motor1.throttle = None
    kit.motor2.throttle = None
    return
""" Next some funcs that just say stuff"""
def repeat_me(text=""):
    to_repeat = text.replace('repeat after me', '', 1)
    say(to_repeat)
    return 
def say_time(text=""):
    now = datetime.now()
    dt_string = now.strftime("Your space time co ordinates are %I %M %p on %A %B %d, %Y.")
    say(dt_string)
    return 
"""
Use the openweathermap API to get weather info. right now have hardcoded a bunch
of stuff, such as the API key, the lat and long for Portland, etc. The API returns info in 
JSON format, which is a nested series of dicts and things. 
"""
def say_weather(text=""):
    api_key = "5295f26a45340d6e3fbf3e63fb069a79"
    base_url = "http://api.openweathermap.org/data/2.5/onecall?"
    full_url = (base_url 
        + "lat=45.5051&lon=-122.6750"
        + "&exclude=hourly,minutely"
        + "&appid=" 
        + api_key 
        + "&units=imperial"
        )
    say("Let me check.") 

    response = requests.get(full_url) 
    data = json.loads(response.text)
    current = data["current"]
    current_temp = current["temp"]
    current_weather = current["weather"]
    current_description = current_weather[0]["description"]
    daily = data["daily"]
    daily_temp = daily[0]["temp"] 
    max_temp = daily_temp["max"]
    min_temp = daily_temp["min"]
    say('Right now in Portland its "%d" degrees Fahrenheit.' % current_temp)
    say('The sky looks "%s" to me.' % current_description)
    say('Forecast calls for a high of "%d", and a low of "%d".' % (max_temp, min_temp))
    return 
def tell_joke(text=""):
    url = r"https://official-joke-api.appspot.com/random_joke"
    data = requests.get(url)
    joke = json.loads(data.text)
    say(joke["setup"]+"...")
    say(joke["punchline"])
    return
def say_fav_show(text=""):
    say("Doctor Who. Obviously!")
    return 
def say_creator(text=""):
    say("Some maniac from Reed College. Between you and me, I think he's got a screw loose.")
    return 
def say_name(text=""):
    say("My name is K9 Mark 3. I'm an experimental project created by Chris Lidgaate.")
    return 
def say_goodbye(text=""):
    global user_name
    say("Goodbye, " + user_name + ". Talk to you later.")
    exit()
    return 
def say_what(text=""):   #this is our generic "i didn't understand" situation
    if not text:
        return 
    else:
        say("Sorry, I don't understand.")
    return 
"""
Next, the "tell me about x" function. User asks for info on a topic and we
look it up in wikipedia. i don't think the wikipedia module is super reliable
and wish we could do better error-checking. there's long latency while we get info.
"""
def tell_me_about(text):
    if not text:
        return
    # so text will be something like "tell me about Delaware."
    # first we have to strip out the 'tell me about' preamble
    topic = text.replace('tell me about', '', 1)
    if not topic:
        say("Sorry, I didn't catch that.")
        return
    say("OK, Hang on a sec while I look up" + topic)
    try:
            wikipedia_entry = wikipedia.summary(topic, sentences=wiki_sentences)
    except wikipedia.exceptions.PageError as e:
            logging.info(e.options)
            say("Page error.")
            return
    except wikipedia.exceptions.DisambiguationError as e:
            logging.info(e.options)
            say("Sorry, that was too ambiguous.")
            return
    say("Here's what I found:")
    say(wikipedia_entry)
    return 
def more_detail(text=""):
    global wiki_sentences
    wiki_sentences = wiki_sentences + 2
    say("Affirmative")
    return 
def less_detail(text=""):
    global wiki_sentences
    wiki_sentences = wiki_sentences - 2
    if wiki_sentences <= 1 :
        wiki_sentences = 1
    say("Affirmative")
    return 
"""
next answer any questions that have stumped us so far. That means the question was not in our 
phraselist. This is explicitly for questions. so 
first let's make sure there is a question word. Let's also kick out
questions about you and me since those are not things the internet is likely to answer well.
at first, tried to post a query to duckduckgo but i don't understand their format
so right now am just asking Alexa!
"""
def answer_question(question=""):
    global k9_volume
    if not question :
        return 0
    qlist = [ 'who','whos','what','whats','which','why','where','wheres','when','whens','how','hows']
    first_word = question.split()[0]
    if first_word not in qlist :
        logging.info('"%s" is not a question.' % question)
        return 0
    shitlist = [ 'you','your','me','my','us','we']
    say("I have no idea.")
    k9_volume = k9_volume + 20  # make it loud!
    say("Alexa! " + question)  
    k9_volume = k9_volume - 20  # back to normal volume
    return 1
"""
    url = 'https://api.duckduckgo.com/?q="%s"&format=json' % question
    logging.info(url)
    data = requests.get(url)
    answer = json.loads(data.text)
    logging.info(answer["AbstractText"])
    say(answer["AbstractText"])
    return 1
    """
"""
Next a func to do some clever responses for users we expect to encounter
"""
def set_user_name(text):
    global user_name
    global user_name_tries
    if text is None:
        user_name_tries+=1
        if user_name_tries <= 3 :
            say("Sorry, I didn't hear that. What is your name?")
            return None
        else :
            say("Still didn't hear it. I'll call you Ishmael.")
            user_name = "Ishmael" 
            user_name_tries = 0
            return user_name       
    else :
        user_name = text.lower()
        if "chris" in user_name:
            say("I thought it might be you, " + user_name + ". What an unexpected pleasure.")
            return user_name       
        elif "alex" in user_name:
            say("I hear you can walk on stilts, " + user_name + ". I would do that but I don't have legs.")
            return user_name       
        elif "theo" in user_name:
            say("I hear you like the beetles, " + user_name + ". My favorite beetle is Paul.")
            return user_name       
        elif "luke" in user_name:
            say("I hear you're good at soccer, " + user_name + ". Maybe one day you'll teach me how to play!")
            return user_name       
        elif "audrey" in user_name:
            say(user_name)
            say("The famous shef? I'm honored. I wish I could join you for dinner, but I don't eat much.")
            return user_name       
        elif "mike" in user_name:
            say("Hey there")
            say(user_name)
            say("How are the trains running?")
            return user_name       
        elif "betty" in user_name:
            say("Hello")
            say(user_name)
            say("You have a wonderful family.")
            return user_name       
        elif "lucy" in user_name:
            say("Hello, " + user_name + ". You are very very fluffy.")
            return user_name       
        else :
            say("Greetings, " + user_name + ". It's a pleasure to meet you.")
            return user_name
    return None
"""
Next set up a dictionary of known phrases user might say and functions K9 might execute in 
response. In python dictionaries have a key:value structure. The phrases are keys and 
the functions are values. The phrase is a string that we can pass to some of these
functions. The keys can be used as hints for voice recognition
"""
phrase_bank = {
    'K9' : wake_up,
    'turn the light on' : light_on, 
    'turn the light off': light_off, 
    'blink the light'   : light_blink, 
    'pulse the light'   : light_pulse, 
    'turn left'   : turn_left, 
    'turn right'   : turn_right, 
    'spin'   : spin, 
    'go forward'   : go_forward, 
    'go back'   : go_back, 
    'back up'   : go_back, 
    'speed up'   : speed_up, 
    'slow down'   : slow_down, 
    'attack'   : attack, 
    'stop'   : halt, 
    'halt'   : halt, 
    'woe'   : halt, 
    'get louder'   : get_louder, 
    'speak up'   : get_louder, 
    'pipe down'   : get_quieter, 
    'too loud'   : get_quieter, 
    'more detail'   : more_detail, 
    'less detail'   : less_detail, 
    'broad strokes'   : less_detail, 
    'repeat after me'   : repeat_me, 
    'what time is it'   : say_time,
    'what\'s the time'  : say_time,
    'what is the weather' : say_weather,
    'what\'s the weather' : say_weather,
    'what is your favorite show'    : say_fav_show,
    'what\'s your favorite show'    : say_fav_show,
    'what\'s your name'     : say_name, 
    'who are you'     : say_name, 
    'who built you'     : say_creator, 
    'who made you'     : say_creator, 
    'who created you'   : say_creator, 
    'tell me about'     : tell_me_about,
    'tell me a joke'    : tell_joke,
    'tell me another joke'    : tell_joke,
    'tell me a better joke'    : tell_joke,
    'say something funny'    : tell_joke,
    'make me laugh'    : tell_joke,
    'see you'           : say_goodbye,
    'chow'              : say_goodbye,
    'goodbye'           : say_goodbye
    }

"""
Next a function that takes a phrase, looks at phrase_bank to see if we know how to handle
and returns appropriate function. Otherwise return the say_what function. Note the phrase
may actually *contain* the key phrase. So if user asks "I say, what time is it, eh?" We 
look to see if the phrase_bank contains "what time is it". We need to figure out how to
strip extraneous stuff from the beginning of phrase, too
"""
def respond_to_phrase(phrase):
    if not phrase:
        return
    for key in phrase_bank :
        if key in phrase :
            func = phrase_bank[key]
            return func(phrase)
    # if we're here, we didn't find phrase in the phrase_bank    
    logging.info('not finding "%s"' % phrase)
    first_word = phrase.split()[0]
    qlist = ['who','what','which','why','where','when','how']
    if first_word in qlist :
        return answer_question(phrase)
    else :
        return(say_what(phrase))

def get_hints(language_code):
    if language_code.startswith('en_'):
        return (phrase_bank.keys())
    return None
"""
Next define a subclass of the cloudspeech client. mostly because I want k9 to show user that
it is "listening" by pulsing an LED.
"""
class K9Client (CloudSpeechClient):
    def start_listening(self):
        k9_board.led.state = Led.PULSE_SLOW
            # Calling the parent's class method, whic basically just logs to the logfile.
        super().start_listening()         
        return 
    def stop_listening(self):
        k9_board.led.state = Led.OFF
        super().stop_listening()         
        return 
"""
Finally, define the main() loop
"""
def main():
    global awake_flag
    mixer.music.load("sine-wave-0.05s.wav") # this soundfile plays short blip
    mixer.music.set_volume(0.2) # make it very quiet
    mixer.music.play()

    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Assistant service example.')
    parser.add_argument('--language', default=locale_language())
    args = parser.parse_args()
    
    logging.info('Initializing for language %s...', args.language)
    hints = get_hints(args.language)
    client = K9Client()
    say_time()
    say("Greetings. This is K-9 Mark Three.")
    say("Please wait until my light starts to blink before you tell me anything.")
    say("What is your name? Wait for the light.")
    text = client.recognize(language_code=args.language,
                                hint_phrases=0)
    set_user_name(text)
    say("Awaiting your instructions. Wait for the light.")
    # now comes the guts of the program. We loop, listening for user to say something
    # that we send to the AIY speech recognition software in the cloud. It magically returns a 
    # text object. that we can inspect. Bizarre, but it works!  
    while True:
        text = client.recognize(language_code=args.language,    # this invokes the speech client.
                                hint_phrases=hints)
        if text is None:
            logging.info('You said nothing.')
            if time.time() - awake_time > bed_time :
                awake_flag = 0
            continue
        # now set up the "K9" hotword.
        first_word = text.split()[0]
        logging.info(first_word)
        if (first_word != 'K9' and awake_flag == 0) :
            logging.info('Ignore. You said %s.' % text) # they didn't say hotword, so ignore
            continue
        if (first_word != 'K9' and awake_flag == 1) :
            logging.info('Awake already. You said %s.' % text) # already awake
            text = text.lower()
            respond_to_phrase(text)
            if time.time() - awake_time > bed_time :
                awake_flag = 0
            continue
        # if we're here, the text begins with K9. If that is all user said, then we should
        # respond by invoking wake_up(). If they said more, then respond_to_phrase().
        if text == 'K9' :
            wake_up()
            continue
        # strip out the K9 and continue.
        else :
            text = text.replace('K9', '', 1)
        # now let's respond to the text
        logging.info('Awaken. You said: "%s"' % text)
        text = text.lower()
        respond_to_phrase(text)
        continue

if __name__ == '__main__':
    main()
