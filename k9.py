#!/usr/bin/env python3

"""
K9 is a roving robot that can respond to voice commands.
Makes heavy use of google aiy voice library
Hardware:
    Raspberry Pi Zero
    Google AIY Voice Bonnet: https://aiyprojects.withgoogle.com/voice/#makers-guide--gpio-header-pinout
    Adafruit Motor bonnet
    Sharp GP2Y0D810Z0F Digital Distance Sensor (2-10 cm) https://www.adafruit.com/product/1927
    robot vacuum chassis
Major libraries:
    aiy.board
    aiy.voice
    wikipedia
    gpiozero (this will be useful for reading sensors)
    https://gpiozero.readthedocs.io/en/stable/api_input.html

"""
import argparse
import locale
import logging
from datetime import datetime

from aiy.board import Board, Led
from aiy.pins import PIN_A, PIN_B, PIN_C, PIN_D, LED_1, LED_2 # pins and leds on the voice board
from aiy.cloudspeech import CloudSpeechClient   # does the speech-recognition magic
import aiy.voice.tts    # does the text-to-speech
import wikipedia        # you can guess. this module actually doesn't work very well.
import requests
import gpiozero # this library handles sensors and leds and stuff
from gpiozero import Button, MotionSensor, LED # obstacle detector
front_sensor = MotionSensor(pin=PIN_A, pull_up=True)    # the sensor fires low when triggered
left_sensor = MotionSensor(pin=PIN_B, pull_up=True)    # the sensor fires low when triggered
right_sensor = MotionSensor(pin=PIN_C, pull_up=True)    # the sensor fires low when triggered
import json
import time
from adafruit_motorkit import MotorKit  # this runs the motor interface
kit = MotorKit()    # feels weird to init this here, but can't figure out where else to do it
left_motor = kit.motor2
right_motor = kit.motor1
LEFT_FORWARD = -1
LEFT_BACKWARD = 1
RIGHT_FORWARD = 1
RIGHT_BACKWARD = -1
motor_speed = 0.4   # this is default speed for motors. 1.0 is max. 

"""
Now declare some global variables. I don't like doing this here but where else?
"""
user_name = "Norbert"   # define global variable for user's name
user_name_tries = 0     # keep track of how many times we've tred to set name
awake_flag = 0          # user has to wake us up by uttering hotword
awake_time = 0          # remember when we woke up
bed_time = 5            # this is how long K9 stays awake 
k9_volume = 5      # sets initial volume. user can tell k9 to get louder/quieter
wiki_sentences = 5 # sets how many sentences to read from wikipedia.
k9_board = Board()  # again, i hate that we have to do this here instead of in an init func
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
    left_motor.throttle = LEFT_FORWARD * motor_speed
    right_motor.throttle = RIGHT_BACKWARD * motor_speed
    say("right")
    while time.time() - start_time < 0.2:  # this executes roughly a quarter turn.
        pass
    left_motor.throttle = None
    right_motor.throttle = None
    return
def turn_left(text=""):
    start_time = time.time()
    left_motor.throttle = LEFT_BACKWARD * motor_speed
    right_motor.throttle = RIGHT_FORWARD * motor_speed
    say("left")
    while time.time() - start_time < 0.2:  # this executes roughly a quarter turn.
        pass
    kit.motor1.throttle = None
    kit.motor2.throttle = None
    return
def attack(text=""):
    say("attack!")
    go_forward("go forward 5")
    return
"""
Now a func where we actually want to read the text object, because it may contain useful info,
such "go forward 7" where the number indicates duration of motion in seconds. 
Of course if they just say "go forward" then we use a default value for the duration. 
"""
def go_forward(text=""):
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
        throttle_duration = 10  # let's set a default max so user can't ask for 1 million seconds     global motor1_direction
    return engage_motor(leftspeed=LEFT_FORWARD * motor_speed,rightspeed=RIGHT_FORWARD * motor_speed,duration=throttle_duration)
def go_back(text=""):
    return engage_motor(leftspeed=LEFT_BACKWARD * motor_speed,rightspeed=RIGHT_BACKWARD * motor_speed,duration=1)
def obstacle_detected():
    logging.info("foo")
    return
"""
engage_motor() is where we actually make the damn thing go back or forward. 
If we detect an obstacle, stop moving and return 0.
There must be prettier ways to do all this but oh well.
"""
def engage_motor(leftspeed=1,rightspeed=1,duration=1):
    global front_sensor
    global left_sensor
    global right_sensor

    if duration > 10 :
        duration = 10  # let's set a default max so user can't ask for 1 million seconds 
    start_time = time.time()
    left_motor.throttle = leftspeed
    right_motor.throttle = rightspeed        
    while time.time() - start_time < duration:
        if front_sensor.motion_detected == True :  # the sensor detects an obstacle
            left_motor.throttle = None
            right_motor.throttle = None
            logging.info("obstacle in front")
            return 0
        elif left_sensor.motion_detected == True :  # the sensor detects an obstacle
            left_motor.throttle = None
            right_motor.throttle = None
            logging.info("obstacle left")
            return 0
        elif right_sensor.motion_detected == True :  # the sensor detects an obstacle
            left_motor.throttle = None
            right_motor.throttle = None
            logging.info("obstacle right")
            return 0
        else :
            pass    # no obstacle, keep looping til we exceed duration.
    left_motor.throttle = None
    right_motor.throttle = None
    return 1
"""
The explore func would lets K9 roam around the room, avoiding obstacles. The basic
idea is to go forward til we sense something, then turn, try again, etc. ideally during the cycle
we would also check to see if user has said something. command would be "explore 30" or sometnng like that.
for now the max time for explore is 100 seconds
"""
def explore(text=""):
    word_list = text.split()
    try :
        second_word = word_list[2] #get the second word
    except :
        second_word = "30"    # there wasn't one. so set to 30 seconds
    try :
        explore_duration = int(second_word)
    except :
        explore_duration = 30 # if int() didn't work, set for 3 seconds
    if explore_duration > 100 :
        explore_duration = 100  # let's set a max so user can't ask for 1 million seconds 
    start_time = time.time()
    left_count = 0
    while time.time() - start_time < explore_duration: # do this for duration seconds tops
        sailing = go_forward("go forward 2") #
        if sailing == 1 :   # no obstacle
            left_count = 0
            continue
        else :   # obstacle!
            left_count = left_count + 1
            if left_count > 5 :
                go_back()
            turn_left()
            continue
    return
"""
don't think we actually need this func any more
"""
def halt(text=""):    
    left_motor.throttle = None
    right_motor.throttle = None
    motor_speed = 0.3
    return
def spin(text=""):  # spin clockwise, then anticlockwise
    start_time = time.time()
    left_motor.throttle = LEFT_FORWARD
    right_motor.throttle = RIGHT_BACKWARD
    say("and around we go")
    while time.time() - start_time < 2.5:
        pass
    left_motor.throttle = None
    right_motor.throttle = None
    while time.time() - start_time < 0.2:
        pass
    left_motor.throttle = LEFT_BACKWARD
    right_motor.throttle = RIGHT_FORWARD
    say("You make me dizzy, miss lizzy!")
    while time.time() - start_time < 2.5:
        pass
    left_motor.throttle = None
    right_motor.throttle = None
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
    try:
        response = requests.get(full_url)
        data = json.loads(response.text)
    except:
        say("Sorry, I'm not sure. Try looking out the window.") 
        return
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
    url = "https://official-joke-api.appspot.com/random_joke"
    try:
        data = requests.get(url)
        joke = json.loads(data.text)
    except:
        say("Sorry, I can't think of one right now.")
        return
    say(joke["setup"]+"..")
    say(joke["punchline"])
    return
def trivia(text=""):
    url = "https://opentdb.com/api.php?amount=1&category=23&difficulty=medium&type=multiple"
    try:
        data = requests.get(url)
        trivia = json.loads(data.text)
    except:
        say("argh.")
        return
    logging.info(trivia.json())
    return
def say_fav_show(text=""):
    say("Doctor Who, obviously!")
    return 
def say_creator(text=""):
    say("Some maniac from Reed College. Between you and me, I think he's got a screw loose.")
    return 
def say_name(text=""):
    say("My name is K9 Mark 3. I'm an experimental robot created by Chris Lidgaate. I can respond to simple commands. I can also tell jokes.")
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
        return -1
    # so text will be something like "tell me about Delaware."
    # first we have to strip out the 'tell me about' preamble
    topic = text.replace('tell me about', '', 1)
    if not topic:
        say("Sorry, I didn't catch that.")
        return -1
    say("OK, Hang on a sec while I look up" + topic)
    try:
        wikipedia_entry = wikipedia.summary(topic, sentences=wiki_sentences)
    except wikipedia.exceptions.PageError as e:
        logging.info(e.options)
        say("Page error.")
        return -1
    except wikipedia.exceptions.DisambiguationError as e:
        logging.info(e.options)
        say("Sorry, that was too ambiguous.")
        return -1
    except :
        say("Sorry, something went wrong.")
        return -1
    say("Here's what I found:")
    say(wikipedia_entry)
    return 1
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
    shitlist = ['you','your','me','my','us','we']
    s = set(question.split()).intersection(shitlist)
    if len(s) != 0 :
        say("That is a personal question.")
        return 0
    say("I have no idea. But I know someone who might know.")
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
    'explore'   : explore,
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
    'identify yourself'     : say_name, 
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
    say("Identify yourself. What is your name? Wait for the blinky light.")
    text = client.recognize(language_code=args.language,
                                hint_phrases=0)
    set_user_name(text)
    say("Awaiting your instructions. Wait for the blinky light.")
    # now comes the guts of the program. We loop, listening for user to say something
    # that we send to the AIY speech recognition software in the cloud. It magically returns a 
    # text object. that we can inspect. Bizarre, but it works!  
    while True:
        if front_sensor.motion_detected == True :
            logging.info("obstacle")
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
