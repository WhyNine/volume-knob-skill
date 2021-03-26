# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/volume-down.svg' card_color='#022B4F' width='50' height='50' style='vertical-align:bottom'/> Volume knob skill

## About
This Mycroft skill is written for the Piminori RGB Encoder, connected to a Raspberry Pi. The encoder includes red, green and blue LEDs, enabling it to light up with any desired colour.

The skill uses the encoder as a volume control. The encoder allows full 360 degree rotation so is used as an incremenetal volume controller, i.e. rotating clockwise increases volume while rotating counterclockwise decreases volume.

The colour and intensity of the LEDs in the knob can be set for when Mycroft is idle (waiting for the wake-up phrase), when it is listening (waiting for a command) and when it is thinking (working out which skill can handle the command).

## Important
This skill is made for Picroft Lightning, which is Picroft on Rasbian Stretch. It requires that I2C is enabled on the Pi via raspi-config.

## Category
**IoT**

## Credits
Simon Waller

## Supported Devices
platform_picroft

## Tags
#volume

