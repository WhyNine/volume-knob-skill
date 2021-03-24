from mycroft import MycroftSkill
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

import RPi.GPIO as GPIO
import ioexpander as io

colours = [[255, 0, 0], [0, 255, 0], [255, 255, 0], [0, 0, 255], [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]]
LOGGER = getLogger(__name__)

I2C_ADDR = 0x0F  # I2C address of the encoder
INTERRUPT_PIN = 4

# Encoder pin definitions
PIN_RED = 1
PIN_GREEN = 7
PIN_BLUE = 2

POT_ENC_A = 12
POT_ENC_B = 3
POT_ENC_C = 11

BRIGHTNESS = 0.5                # Effectively the maximum fraction of the period that the LED will be on
PERIOD = int(255 / BRIGHTNESS)  # Add a period large enough to get 0-255 steps at the desired brightness

knob = 0

class VolumeKnobSkill(MycroftSkill):

    def set_colour(self, colour, intensity):
        [r, g, b] = colours[colour]
        self.ioe.output(PIN_RED, int(r * intensity/100))
        self.ioe.output(PIN_GREEN, int(g * intensity/100))
        self.ioe.output(PIN_BLUE, int(b * intensity/100))

    def led_idle(self):
        LOGGER.info("Change LED to IDLE colour")
        self.set_colour(self.ledidlecolour, self.ledidleintensity)

    def led_listen(self):
        LOGGER.info("Change LED to LISTEN colour")
        self.set_colour(self.ledlistencolour, self.ledlistenintensity)

    def led_think(self):
        LOGGER.info("Change LED to THINK colour")
        self.set_colour(self.ledthinkcolour, self.ledthinkintensity)

    def __init__(self):
        MycroftSkill.__init__(self)

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.get_settings()
        try:
            self.ioe = io.IOE(i2c_addr=I2C_ADDR, interrupt_pin=4)
            self.ioe.enable_interrupt_out(pin_swap=True)
            self.ioe.setup_rotary_encoder(1, POT_ENC_A, POT_ENC_B, pin_c=POT_ENC_C)
            self.ioe.set_pwm_period(PERIOD)
            self.ioe.set_pwm_control(divider=2)
            self.ioe.set_mode(PIN_RED, io.PWM, invert=True)
            self.ioe.set_mode(PIN_GREEN, io.PWM, invert=True)
            self.ioe.set_mode(PIN_BLUE, io.PWM, invert=True)
            knob = self.ioe.read_rotary_encoder(1)
            GPIO.setwarnings(False)
            GPIO.setup(INTERRUPT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.remove_event_detect(INTERRUPT_PIN)
            GPIO.add_event_detect(INTERRUPT_PIN, GPIO.FALLING)
            self.led_idle()
        except:
            LOGGER.warning("Can't initialize GPIO - skill will not load")
            self.speak_dialog("error.initialize")
            return
        self.schedule_repeating_event(self.knob, None, 0.1, 'VolumeKnob')
        self.add_event('recognizer_loop:record_begin', self.on_listener_started)
        self.add_event('recognizer_loop:record_end', self.on_listener_ended)
        self.add_event('mycroft.skill.handler.complete', self.on_handler_complete)
        self.add_event('mycroft.speech.recognition.unknown', self.on_handler_complete)

    def knob(self, message):
        if GPIO.event_detected(INTERRUPT_PIN):
            LOGGER.info("Detected knob interrupt")
            self.ioe.clear_interrupt()
            new_knob = self.ioe.read_rotary_encoder(1)
            LOGGER.debug(f"Knob values: new = {new_knob}, old = {knob}")
            if new_knob > knob:
                self.bus.emit(Message('mycroft.volume.increase', {"play_sound": False}))
            if new_knob < knob:
                self.bus.emit(Message('mycroft.volume.decrease', {"play_sound": False}))
            knob = new_knob

    def on_listener_started(self, message):
        self.led_listen()

    def on_listener_ended(self, message):
        self.led_think()

    def on_handler_complete(self, message):
        self.led_idle()

    def on_settings_changed(self):
        self.get_settings()
        self.led_idle()
        
    def get_settings(self):
        self.ledidlecolour = int(self.settings.get('ledidlecolour', 1))
        self.ledidleintensity = self.settings.get('ledidleintensity', 100)
        if self.ledidleintensity < 0: self.ledidleintensity = 0 
        if self.ledidleintensity > 100: self.ledidleintensity = 100 
        self.ledlistencolour = int(self.settings.get('ledlistencolour', 2))
        self.ledlistenintensity = self.settings.get('ledlistenintensity', 100)
        if self.ledlistenintensity < 0: self.ledlistenintensity = 0 
        if self.ledlistenintensity > 100: self.ledlistenintensity = 100
        self.ledthinkcolour = int(self.settings.get('ledthinkcolour`', 2))
        self.ledthinkintensity = self.settings.get('ledthinkintensity', 100)
        if self.ledthinkintensity < 0: self.ledthinkintensity = 0 
        if self.ledthinkintensity > 100: self.ledthinkintensity = 100


def create_skill():
    return VolumeKnobSkill()
