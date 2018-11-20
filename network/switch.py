#!/usr/bin/python3
# coding: utf-8

from network.group import Group

import paho.mqtt.client as mqtt
from threading import Thread
import time
from log import logger
import paho.mqtt.subscribe as subscribe
import json
import random
import string

class Switch(Thread):

    def __init__(self, broker_ip):
        Thread.__init__(self)
        self.broker_ip = broker_ip
        self.groups = {}
        self.drivers = {
            "leds" : {},
            "sensors": {},
            "blinds": {}
        }
        self.diagnostic = {
            "config": {},
            "events": {}
        }
        self.name = "Switch" + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Unexpected client disconnect for %r, will reconnect", self.name)

    def run(self):
        self.client = mqtt.Client(self.name)
        self.client.on_message = self.event_received
        self.client.on_disconnect = self.on_disconnect
        self.client.connect(self.broker_ip)
        self.client.loop_start()
        subscribe.callback(self.event_received, "#", hostname=self.broker_ip)

        while self.is_alive:
            time.sleep(1)
        self.client.loop_stop()

    def event_received(self, client, userdata, message):
        try:
            data = message.payload.decode("utf-8")
            logger.debug("received url  %r %r", message.topic, str(data))
            if message.topic.endswith("/setup/hello"):
                data = json.loads(data)
                topic_url = data["topic"] + "/setup/config"
                config = {}
                if data["type"] == "led":
                    config["iMax"] = 700
                self.client.publish("/write/" + topic_url, json.dumps(config))
        except:
            logger.exception("Invalid value received")

    def create_group(self, leds, sensors, blinds, group_id):
        if group_id in self.groups:
            return False

        group = Group(self.broker_ip, group_id)
        self.groups[group_id] = group

        for led in leds:
            group.add_led(led)

        for sensor in sensors:
            group.add_sensor(sensor)

        for blind in blinds:
            group.add_blind(blind)

        group.start()
        self.diagnostic['events'][time.time()] = "Group " + str(group_id) + "has been created and contains " + json.dumps(group.serialize())
        return True

    def add_driver_to_group(self, group_id, driver_type, mac):
        if group_id not in self.groups:
            return False

        group = self.groups[group_id]

        if driver_type == "led":
            led = self.get_led(mac)
            if not led:
                return False
            return group.add_led(led)
        elif driver_type == "sensor":
            sensor = self.get_sensor(mac)
            if not sensor:
                return False
            return group.add_sensor(sensor)
        elif driver_type == "blind":
            blind = self.get_blind(mac)
            if not blind:
                return False
            return group.add_blind(blind)
        self.diagnostic['events'][time.time()] = "Driver " + driver_type + " : " + mac + "has been been added to " + group_id
        return False

    def get_group_id(self, group_id):
        if group_id in self.groups:
            return self.groups[group_id]
        return {}

    def list_groups(self):
        return self.groups.values()

    def update_group_rules(self, group_id, rule_id, value):
        if group_id not in self.groups:
            return False
        if rule_id == "brightness":
            self.groups[group_id].set_brightness(value)
        elif rule_id == "temperature":
            self.groups[group_id].set_temperature(value)
        elif rule_id == "presence":
            self.groups[group_id].set_presence(value)
        self.diagnostic['events'][time.time()] = "Rule " + rule_id + " is set to " + str(value) + " for " + str(group_id)
        return True

    def list_leds(self):
        return self.drivers["leds"].values()

    def get_led(self, led_id):
        if led_id in self.drivers["leds"]:
            return self.drivers["leds"][led_id]
        return None

    def plug_led(self, led):
        self.drivers["leds"][led.mac] = led
        self.diagnostic['events'][time.time()] = "New led " + led.mac + " has been plugged into the switch"

    def unplug_led(self, led):
        if led.mac in self.drivers["leds"]:
            del self.drivers["leds"][led.mac]
        self.diagnostic['events'][time.time()] = "Led " + led.mac + " has been unplugged from the switch"

    def list_sensors(self):
        return self.drivers["sensors"].values()

    def get_sensor(self, sensor_id):
        if sensor_id in self.drivers["sensors"]:
            return self.drivers["sensors"][sensor_id]
        return None

    def plug_sensor(self, sensor):
        self.drivers["sensors"][sensor.mac] = sensor
        self.diagnostic['events'][time.time()] = "New sensor " + sensor.mac + " has been plugged into the switch"

    def unplug_sensor(self, sensor):
        if sensor.mac in self.drivers["sensors"]:
            del self.drivers["sensors"][sensor.mac]
        self.diagnostic['events'][time.time()] = "Sensor " + sensor.mac + " has been unplugged from the switch"

    def switch_led_mode(self, led_id, auto=True):
        if led_id not in self.drivers["leds"]:
            return False
        led = self.drivers["leds"][led_id]
        url = "/write/" + led.base_topic + "/status/auto"
        logger.info("Send switch mode to %r for %r", auto, url)
        status = "auto"
        if not auto:
            status = "manual"
        self.diagnostic['events'][time.time()] = "Switch led " + led.mac + " into mode " + status
        self.client.publish(url,  "%s" % auto)
        return True

    def list_blinds(self):
        return self.drivers["blinds"].values()

    def get_blind(self, blind_id):
        if blind_id in self.drivers["blinds"]:
            return self.drivers["blinds"][blind_id]
        return None

    def plug_blind(self, blind):
        self.drivers["blinds"][blind.mac] = blind
        self.diagnostic['events'][time.time()] = "New blind " + blind.mac + " has been plugged into the switch"

    def unplug_blind(self, blind):
        if blind.mac in self.drivers["blinds"]:
            del self.drivers["blinds"][blind.mac]
        self.diagnostic['events'][time.time()] = "Blind " + blind.mac + " has been unplugged from the switch"

    def get_diagnostic(self):
        self.diagnostic["config"]["groups"] = [group.serialize() for group in self.groups.values()]
        return self.diagnostic

    def set_manual_led_brightness(self, led_id, brightness=0):
        if led_id not in self.drivers["leds"]:
            return False
        led = self.drivers["leds"][led_id]
        url = "/write/" + led.base_topic + "/base/setpointManual"
        logger.info("Send setpoint to %r for %r", brightness, url)
        self.diagnostic['events'][time.time()] = "Force led " + led.mac + " brightness " + str(brightness)
        logger.info(" back %r", self.client.publish(url, str(brightness)))
        return True

    def switch_blind_mode(self, blind_id, auto=True):
        if blind_id not in self.drivers["blinds"]:
            return False
        blind = self.drivers["blinds"][blind_id]
        url = "/write/" + blind.base_topic + "/status/auto"
        logger.info("Send switch mode to %r for %r", auto, url)
        status = "auto"
        if not auto:
            status = "manual"
        self.diagnostic['events'][time.time()] = "Switch blind " + blind.mac + " into mode " + status
        self.client.publish(url, "%s" % auto)
        return True

    def set_manual_blind_position(self, blind_id, position, blind_number=0):
        if blind_id not in self.drivers["blinds"]:
            return False
        blind = self.drivers["blinds"][blind_id]
        if not blind_number or blind_number == 1:
            url = "/write/" + blind.base_topic + "/base/blind1Manual"
            logger.info("Send position to %r for %r", position, url)
            self.diagnostic['events'][time.time()] = "Force blind " + blind.mac + " position " + str(position)
            self.client.publish(url, str(position))
        if not blind_number or blind_number == 2:
            url = "/write/" + blind.base_topic + "/base/blind2Manual"
            logger.info("Send position to %r for %r", position, url)
            self.diagnostic['events'][time.time()] = "Force blind " + blind.mac + " position " + str(position)
            self.client.publish(url, str(position))

    def set_manual_blind_fin(self, blind_id, fin, blind_number=0):
        if blind_id not in self.drivers["blinds"]:
            return False
        blind = self.drivers["blinds"][blind_id]
        if not blind_number or blind_number == 1:
            url = "/write/" + blind.base_topic + "/base/fin1Manual"
            logger.info("Send position to %r for %r", fin, url)
            self.diagnostic['events'][time.time()] = "Force blind " + blind.mac + " fin " + str(fin)
            self.client.publish(url, str(fin))
        if not blind_number or blind_number == 2:
            url = "/write/" + blind.base_topic + "/base/fin2Manual"
            logger.info("Send position to %r for %r", fin, url)
            self.diagnostic['events'][time.time()] = "Force blind " + blind.mac + " fin " + str(fin)
            self.client.publish(url, str(fin))

    def switch_group_mode(self, group_id, auto=True):
        if group_id not in self.groups:
            return False
        group = self.groups[group_id]
        url = "/write/" + group.base_topic + "/status/auto"
        logger.info("Send switch mode to %r for %r", auto, url)
        status = "auto"
        if not auto:
            status = "manual"
        self.diagnostic['events'][time.time()] = "Switch group " + str(group.group_id) + " into mode " + str(status)
        self.client.publish(url, "%s" % auto)
        return True

    def set_group_setpoint(self, group_id, setpoint):
        if group_id not in self.groups:
            return False
        group = self.groups[group_id]
        url = "/write/" + group.base_topic + "/config/setpoint"
        logger.info("Send setpoint value to %r for %r", setpoint, url)
        self.diagnostic['events'][time.time()] = "Send setpoint " + str(setpoint) + " to group " + str(group.group_id)
        self.client.publish(url, str(setpoint))
        return True

    def set_group_blind_position(self, group_id, position):
        if group_id not in self.groups:
            return False
        group = self.groups[group_id]
        url = "/write/" + group.base_topic + "/config/blindPosition"
        logger.info("Send setpoint value to %r for %r", position, url)
        self.diagnostic['events'][time.time()] = "Send blind position " + str(position) + " to group " + str(group.group_id)
        self.client.publish(url, str(position))
        return True
