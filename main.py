# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import board
import busio
import os
import microcontroller
import time
import binascii

from digitalio import DigitalInOut
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_socket as socket

import adafruit_logging
import adafruit_tca9548a
import adafruit_adt7410

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

def initWiFi(debug=False):
    # If you are using a board with pre-defined ESP32 Pins:
    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    if (debug == True):
        if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
            print("ESP32 found and in idle mode")
        print("Firmware vers.", esp.firmware_version)
        print("MAC addr:", [hex(i) for i in esp.MAC_address])

    #for ap in esp.scan_networks():
    #    print("\t%s\t\tRSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))

    print("Connecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
        except OSError as e:
            print("could not connect to AP, retrying: ", e)
            continue
    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
    print("My IP address is", esp.pretty_ip(esp.ip_address))
    if (debug == True):
        print(
            "IP lookup adafruit.com: %s" % esp.pretty_ip(esp.get_host_by_name("adafruit.com"))
        )
        print("Ping google.com: %d ms" % esp.ping("google.com"))

#   this gets done in MQTT
#    socket.set_interface(esp)
    return esp

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def mqtt_connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to MQTT broker! ")
    #print("Connected to MQTT broker! Listening for topic changes on %s" % onoff_feed)
    # Subscribe to all changes on the onoff_feed.
    #client.subscribe("$SYS/broker/uptime")

def mqtt_disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print("Disconnected from broker!")

def mqtt_message(client, topic, message):
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print("New message on topic {0}: {1}".format(topic, message))

def initMQTT(theEsp):
    # Initialize MQTT interface with the esp interface
    # MQTT really wants to use socketpools, but the ESP32SPI doesn't
    # (appearently) support pools. There is a "legacy" API that
    # allows MQTT to go and acces the older socket api. This next line
    # asks MQTT to set up the globals that it uses when it can't find
    # a socket pool

    MQTT.set_socket(socket, theEsp)

    # Set up a MiniMQTT Client
    mqtt_client = MQTT.MQTT(
        broker="192.168.200.2",
        port=1883,
    )

    # Figure out WTF the mqtt client thinks it's doing
    # mqtt_client.enable_logger(adafruit_logging, 10)
    # Setup the callback methods above
    mqtt_client.on_connect = mqtt_connected
    mqtt_client.on_disconnect = mqtt_disconnected
    mqtt_client.on_message = mqtt_message
    # on_publish
    # on_subscribe
    # on_unsubscribe

    # Connect the client to the MQTT broker.
    print("Connecting to MQTT broker...")
    mqtt_client.connect()
    print("MQTT init complete")
    return mqtt_client

def I2C_scan(i2c):
    # To use default I2C bus (most boards)


    while not i2c.try_lock():
        pass

    try:
        print(
            "I2C addresses found:",
            [hex(device_address) for device_address in i2c.scan()],
        )
        time.sleep(2)

    finally:  # unlock the i2c bus when ctrl-c'ing out of the loop
        i2c.unlock()

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
    print("*\n*\n*\n*\n*\n*\n")
    mqttPrefix = "household/"

    # get the unique identifier for the mqtt topic registration
    uid = microcontroller.cpu.uid
    uid = uid[8:]
    uidName = list(uid)
    print(uidName)
    #uidName = binascii.hexlify(bytearray(uid))
    uidName2 = ''.join(f'{i:02x}' for i in list(uid))
    print(uidName2)
    mqttPrefix = mqttPrefix + uidName2 + "/pyportal/"

    myEsp = initWiFi()
    myClient = initMQTT(myEsp)
    i2c = board.I2C()  # uses board.SCL and board.SDA
    I2C_scan(i2c)

    myMux = adafruit_tca9548a.TCA9548A(i2c)
    for channel in range(8):
        if myMux[channel].try_lock():
            print("Channel {}:".format(channel), end="")
            addresses = myMux[channel].scan()
            print([hex(address) for address in addresses if address != 0x70])
            myMux[channel].unlock()

    photocell_val = 0

    adt = adafruit_adt7410.ADT7410(i2c, address=0x48)
    adt.high_resolution = True

    print(adt.temperature)


    while True:
        # Poll the message queue
        print("Off to loop")
        try:
            myClient.loop()
        except Exception as inst:
            print("Error in loop")
            print(type(inst))
            print(inst.args)
            print(inst)
            raise Exception("Fuck")

        # Send a new message
        print("Sending photocell value: %d..." % photocell_val)
        myClient.publish(mqttPrefix+"photocell_feed", photocell_val)
        myClient.publish(mqttPrefix+"temperature", adt.temperature)
        print("Sent!")
        photocell_val += 1
        time.sleep(30)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
