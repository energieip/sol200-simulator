#!/usr/bin/python3
# coding: utf-8

import paho.mqtt.client as mqtt
from network.driver import error_management
from threading import Thread
import time
import json
import random

from log import logger
from distutils.util import strtobool

class Group(Thread):

    def __init__(self, broker_ip, group_id):
        Thread.__init__(self)
        self.group_id = group_id
        self.broker_ip = broker_ip
        self.base_topic = "group/" + str(self.group_id)
        self.auto = False

        self.current_temperature = 0
        self.current_brightness = 0  # in Lux

        self.slope_start = 10
        self.slope_stop = 10
        self.slope = 0
        self.time_to_auto = 0
        self.watchdog = 60

        self.setpoint = 0
        self.new_setpoint = 0
        self.refresh_light = True

        self.presence = False
        self.time_leaving = 0

        self.empty_room = True

        self.sensors = {}
        self.leds = {}
        self.blinds = {}

        self.rules = {}

        self.url_auto = "/write/" + self.base_topic + "/status/auto"
        self.url_setpoint = "/write/" + self.base_topic + "/config/setpoint"
        self.url_blind_position = "/write/" + self.base_topic + "/config/blindPosition"

        group_name = "Group" + str(self.group_id) + str(random.randint(0,9))
        self.client = mqtt.Client(group_name)
        self.client.on_message = self.event_received
        self.client.connect(self.broker_ip)
        self.client.loop_start()
        self.client.subscribe("#")
        self.client.message_callback_add(self.url_auto, self.update_auto_mode)
        self.client.message_callback_add(self.url_setpoint, self.update_led_brigthness)
        self.client.message_callback_add(self.url_blind_position, self.update_blind_position)

    @error_management
    def update_auto_mode(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        old_state = self.auto
        self.auto = strtobool(data) == 1
        if self.auto == old_state:
            logger.info("Switch group is auto ? %r", self.auto)
            return
        if self.auto:
            #  Switch in automatic mode
            self.time_to_auto = 0
            logger.info("Switch group to automatic mode")
        else:
            # Switch in manual mode
            self.time_to_auto = self.watchdog
            logger.info("Switch group to manual mode, start timer to %r", self.time_to_auto)

    @error_management
    def update_blind_position(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        if self.auto:
            logger.warning("Received update position but the group is in auto mode")
            return
        position = int(data)
        if position not in [0, 1, 2]:
            logger.warning("Received invalid position %r", position)
            return
        for blind in self.blinds:
            base_topic = self.blinds[blind]["topic"]
            url = "/write/" + base_topic + "/base/blind1"
            self.client.publish(url, position)
            url = "/write/" + base_topic + "/base/blind2"
            self.client.publish(url, position)
    
    @error_management
    def update_led_brigthness(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        if self.auto:
            logger.warning("Received update led setpoint but the group is in auto mode")
            return
        setpoint = int(data)
        if setpoint < 0 or setpoint > 100:
            logger.warning("Received invalid setpoint %r", setpoint)
            return
        self.new_setpoint = setpoint
        if self.setpoint > self.new_setpoint:
            self.slope = self.slope_stop
        else:
            self.slope = self.slope_start
        self.refresh_light = False

    def serialize(self):
        return {
            "group": self.group_id,
            "leds": [led for led in self.leds],
            "sensors": [sensor for sensor in self.sensors],
            "blinds": [blind for blind in self.blinds],
            "rules": self.rules,
            "slopeStart": self.slope_start,
            "slopeStop": self.slope_stop,
            "auto": self.auto,
            "timeToAuto": self.time_to_auto,
            "watchdog": self.watchdog
        }

    def event_received(self, client, userdata, message):
        try:
            logger.debug("Group Received %r %r", message.topic, message.payload.decode("utf-8"))
            data = message.payload.decode("utf-8")
            source = message.topic.split("/")[3]
            if source in self.sensors:
                dump = json.loads(data)
                if "temperature" in dump:
                    self.sensors[source]["temperature"] = int(dump["temperature"])
                    self.compute_temperature()
                if "brightness" in dump:
                    self.sensors[source]["brightness"] = int(dump["brightness"])
                    self.compute_brightness()
                if "presence" in dump:
                    self.sensors[source]["presence"] = bool(dump["presence"])
                    self.compute_presence()
            elif source in self.leds:
                pass
        except:
            logger.exception("Received invalid value")

    def run(self):
        while self.is_alive:
            if self.time_to_auto <= 0:
                # Switch back to automatic mode
                self.auto = True
                logger.info("Switch Group %r back to automatic mode", self.group_id)
            if self.time_to_auto:
                self.time_to_auto -= 1

            if self.auto and "temperature" in self.rules:
                if self.current_temperature > self.rules["temperature"]:
                    logger.debug("Start air conditionning")
                elif self.current_temperature < self.rules["temperature"]:
                    logger.debug("Start hitting system")
            
            if self.auto and "presence" in self.rules:
                if self.time_leaving >= self.rules["presence"] and not self.empty_room:
                    self.leave_room()
                    self.empty_room = True
                else:
                    if not self.presence:
                        self.time_leaving += 1
                    else:
                        self.time_leaving = 0
                        self.empty_room = False

            if self.auto and not self.empty_room and self.refresh_light:
                if "brightness" in self.rules:
                    if self.current_brightness < self.rules["brightness"]:
                        logger.debug("Increase brightness")
                        self.increase_brightness()
                        self.refresh_light = False

                    elif self.current_brightness > self.rules["brightness"]:
                        logger.debug("Decrease brightness")
                        self.decrease_brightness()
                        self.refresh_light = False

            diff = self.new_setpoint - self.setpoint
            if diff == 0:
                self.refresh_light = True
                time.sleep(1)
                continue
            
            if self.slope > 0:
                self.setpoint += int((diff / self.slope))
                self.slope -= 1
            else:
                self.setpoint = self.new_setpoint
            logger.info("Set brightness now to %r, Remaining time %r", self.setpoint, self.slope)
            if self.setpoint < 0:
                self.setpoint = 0
            if self.setpoint > 100:
                self.setpoint = 100

            for led in self.leds:
                base_topic = self.leds[led]["topic"]
                url = "/write/" + base_topic + "/base/setpoint"
                self.client.publish(url,  self.setpoint)

            time.sleep(1)
        self.client.loop_stop()

    def add_led(self, led):
        self.leds[led.mac] = {"topic": led.base_topic}
        self.client.subscribe("/read/" + led.base_topic + "/#")
        led.group = self.group_id
        led.auto = True
        logger.info("led %r added", led.serialize())
        return True

    def remove_led(self, led):
        self.client.unsubscribe("/read/" + led.base_topic + "/#")
        if led.base_topic in self.leds:
            del self.leds[led.base_topic]
        led.group = 1
        led.auto = False
        return True

    def increase_brightness(self, scale=10):
        if self.setpoint >= 100:
            return
        self.new_setpoint += scale
        if self.new_setpoint >= 0:
            self.new_setpoint = 100
        self.slope = self.slope_start

    def decrease_brightness(self, scale=10):
        if self.setpoint <= 0:
            return
        self.new_setpoint -= scale
        if self.new_setpoint < 0:
            self.new_setpoint = 0
        self.slope = self.slope_stop

    def leave_room(self):
        logger.info("The room is now empty")
        self.new_setpoint = 0
        self.slope = self.slope_stop

    def add_sensor(self, sensor):
        self.sensors[sensor.mac] = {"topic": sensor.base_topic}
        self.client.subscribe("/read/" + sensor.base_topic + "/#")
        sensor.group = self.group_id
        sensor.auto = True
        logger.info("sensor %r added", sensor.serialize())

    def remove_sensor(self, sensor):
        self.client.unsubscribe("/read/" + sensor.base_topic + "/#")
        if sensor.base_topic in self.sensors:
            del self.sensors[sensor.base_topic]
        sensor.group = 1
        sensor.auto = False
        return True

    def compute_temperature(self):
        active_sensors = 0
        temperature = 0
        for sensor in self.sensors:
            if "temperature" not in self.sensors[sensor]:
                continue
            temperature += self.sensors[sensor]["temperature"]
            active_sensors += 1
        if active_sensors < 1:
            self.current_temperature = 0
        else:
            self.current_temperature = temperature / active_sensors

    def set_temperature(self, ref_temperature):
        self.rules["temperature"] = ref_temperature

    def compute_brightness(self):
        active_sensors = 0
        brightness = 0
        for sensor in self.sensors:
            if "brightness" not in self.sensors[sensor]:
                continue
            brightness += self.sensors[sensor]["brightness"]
            active_sensors += 1
        if active_sensors < 1:
            self.current_brightness = 0
        else:
            self.current_brightness = int(brightness / active_sensors)

    def set_brightness(self, ref_brightness):
        self.rules["brightness"] = ref_brightness
        logger.info("Group %r : brightness rule set to %r", self.group_id, self.rules["brightness"])

    def set_presence(self, ref_presence):
        self.rules["presence"] = ref_presence
        logger.info("Group %r : presence rule set to %r", self.group_id, self.rules["presence"])

    def add_blind(self, blind):
        self.blinds[blind.mac] = {"topic": blind.base_topic}
        self.client.subscribe("/read/" + blind.base_topic + "/#")
        blind.group = self.group_id
        blind.auto = True
        logger.info("blind %r added", blind.serialize())
        return True

    def remove_blind(self, blind):
        self.client.unsubscribe("/read/" + blind.base_topic + "/#")
        if blind.base_topic in self.blinds:
            del self.blinds[blind.base_topic]
        blind.group = 1
        blind.auto = False
        return True

    def compute_presence(self):
        for sensor in self.sensors:
            if "presence" not in self.sensors[sensor]:
                continue
            if self.sensors[sensor]["presence"]:
                self.presence = True
                return
        self.presence = False
