# Copyright Simon Waller
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from mycroft import MycroftSkill
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

from alsaaudio import Mixer, mixers as alsa_mixers
import RPi.GPIO as GPIO
import ioexpander as io

colours = [[255, 0, 0], [0, 255, 0], [255, 255, 0], [0, 0, 255], [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]]
LOGGER = getLogger(__name__)

I2C_ADDR = 0x0F  # I2C address of the encoder
INTERRUPT_PIN = 4

# Encoder pin definitions
LED_RED = 1
LED_GREEN = 7
LED_BLUE = 2

KNOB_A = 12
KNOB_B = 3
KNOB_C = 11


class VolumeKnobSkill(MycroftSkill):

    def set_colour(self, colour, intensity):
        [r, g, b] = colours[colour]
        try:
            self.ioe.output(LED_RED, int(r * intensity/100))
            self.ioe.output(LED_GREEN, int(g * intensity/100))
            self.ioe.output(LED_BLUE, int(b * intensity/100))
        except:
            LOGGER.info("Error while trying to update knob colours")

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
        self._mixer = None

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.get_settings()
        try:
            self.ioe = io.IOE(i2c_addr=I2C_ADDR, interrupt_pin=4)
            self.ioe.enable_interrupt_out(pin_swap=True)
            self.ioe.setup_rotary_encoder(1, KNOB_A, KNOB_B, pin_c=KNOB_C)
            self.ioe.set_pwm_period(510)
            self.ioe.set_pwm_control(divider=2)
            self.ioe.set_mode(LED_RED, io.PWM, invert=True)
            self.ioe.set_mode(LED_GREEN, io.PWM, invert=True)
            self.ioe.set_mode(LED_BLUE, io.PWM, invert=True)
            self.knob = self.ioe.read_rotary_encoder(1)
            GPIO.setwarnings(False)
            GPIO.setup(INTERRUPT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.remove_event_detect(INTERRUPT_PIN)
            GPIO.add_event_detect(INTERRUPT_PIN, GPIO.FALLING)
            self.led_idle()
        except:
            LOGGER.warning("Can't initialize GPIO - skill will not load")
            self.speak_dialog("error.initialize")
            return
        self.schedule_repeating_event(self.volume, None, 0.1, 'VolumeKnob')
        self.add_event('recognizer_loop:record_begin', self.on_listener_started)
        self.add_event('recognizer_loop:record_end', self.on_listener_ended)
        self.add_event('mycroft.skill.handler.complete', self.on_handler_complete)
        self.add_event('mycroft.speech.recognition.unknown', self.on_handler_complete)

    def _get_mixer(self):
        LOGGER.debug('Finding Alsa Mixer for control...')
        mixer = None
        try:
            mixers = alsa_mixers()
            if len(mixers) == 1:
                mixer = Mixer(mixers[0])
            elif 'Master' in mixers:
                mixer = Mixer('Master')
            elif 'PCM' in mixers:
                mixer = Mixer('PCM')
            elif 'Digital' in mixers:
                mixer = Mixer('Digital')
            else:
                # should be equivalent to 'Master'
                mixer = Mixer()
        except Exception:
            # Retry instanciating the mixer with the built-in default
            try:
                mixer = Mixer()
            except Exception as e:
                LOGGER.error('Couldn\'t allocate mixer, {}'.format(repr(e)))
        self._mixer = mixer
        return mixer

    def mixer(self):
        if self._mixer is None:
            return self._get_mixer()
        return self._mixer

    def set_volume(self, vol):
        if self.mixer():
            LOGGER.debug(vol)
            self._mixer.setvolume(vol)

    def get_volume(self, default=50):
        vol = default
        if self.mixer():
            vol = min(self._mixer.getvolume()[0], 100)
            LOGGER.debug('Current volume: {}'.format(vol))
        return vol

    def volume(self, message):
        if GPIO.event_detected(INTERRUPT_PIN):
            LOGGER.debug("Detected knob interrupt")
            self.ioe.clear_interrupt()
            try:
                new_knob = self.ioe.read_rotary_encoder(1)
            except:
                LOGGER.info("Error while trying to read knob value")
                return
            LOGGER.debug(f"Knob values: new = {new_knob}, old = {self.knob}")
            vol_level = self.get_volume()
            LOGGER.debug(f"Volume level read as {vol_level}")
            if (new_knob > self.knob) and (vol_level < 100):
                vol_level += 5
                if vol_level > 100: vol_level = 100
                self.set_volume(vol_level)
                LOGGER.info(f"Volume set to {vol_level}")
            if (new_knob < self.knob) and (vol_level > 0):
                vol_level -= 5
                if vol_level < 0: vol_level = 0
                self.set_volume(vol_level)
                LOGGER.info(f"Volume set to {vol_level}")
            self.knob = new_knob

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
