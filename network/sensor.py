#!/usr/bin/python3
# coding: utf-8

import paho.mqtt.client as mqtt

from network.driver import Driver, error_management
import time
import json
from log import logger
from distutils.util import strtobool

class Sensor(Driver):

    def __init__(self, broker_ip, mac, version):
        Driver.__init__(self, broker_ip, "sensor/" + mac, mac, version)
        self.presence = False
        self.old_presence = False
        self.brightness_correction_factor = 1
        self.thresold_presence = 60
        self.temperature_offset = 0
        self.brightness_raw = 0
        self.last_movment = 0
        self.temperature_raw = 0

        self.url_temperature = self.url_base + "/temperature"
        self.url_brightness = self.url_base + "/brightness"
        self.url_presence = self.url_base + "/presence"
        self.url_brightness_correction_factor = self.url_config + "/brightnessCorrectionFactor"
        self.url_version = self.url_config + "/version"
        self.url_is_configured = self.url_config + "/isConfigured"
        self.url_thresold_presence = self.url_config + "/thresoldPresence"
        self.url_group = self.url_config + "/group"
        self.url_temperature_offset = self.url_config + "/temperatureOffset"
        self.url_brightness_raw = self.url_metric + "/brightnessRaw"
        self.url_last_movment = self.url_metric + "/lastMovment"
        self.url_voltage_input = self.url_metric + "/voltageInput"
        self.url_temperature_raw = self.url_metric + "/temperatureRaw"
        self.url_ble = self.url_config + "/isBleEnabled"
        self.url_reset_numbers = self.url_metric + "/resetNumbers"
        self.url_initial_date = self.url_metric + "/initialSetupDate"
        self.url_last_reset = self.url_metric + "/lastResetDate"

    def serialize(self):
        sensor = {
            "mac": self.mac,
            "isConfigured": self.is_configured,
            "error": self.error,
            "initialSetupDate": self.initial_date
        }
        if self.is_configured:
            sensor["group"] = self.group
            sensor["presence"] = self.presence
            sensor["temperatureOffset"] = self.temperature_offset
            sensor["temperature"] = self.temperature_raw - self.temperature_offset
            sensor["brightness"] = self.brightness_raw * self.brightness_correction_factor
            sensor["brightnessCorrectionFactor"] = self.brightness_correction_factor
            sensor["version"] = self.version
            sensor["thresoldPresence"] = self.thresold_presence
            sensor["brightnessRaw"] = self.brightness_raw
            sensor["lastMovment"] = self.last_movment
            sensor["voltageInput"] = self.voltage_input
            sensor["temperatureRaw"] = self.temperature_raw
            sensor["resetNumbers"] = self.reset_numbers
            sensor["lastResetDate"] = self.last_reset_date
            sensor["isBleEnabled"] = self.is_ble_enabled
        return sensor

    @error_management
    def setup_configuration(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        config = json.loads(data)
        logger.info("Not yet implemented setup_configuration for sensor %r", config)
        self.is_configured = True

    @error_management
    def update_brightness_correction_factor(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.brightness_correction_factor = int(data)

    @error_management
    def update_configuration_status(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        # Field used for reset to default
        self.is_configured = strtobool(data) == 1
        self.reset_numbers += 1
        self.last_reset_date = time.time()

    @error_management
    def enable_ble(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.is_ble_enabled = strtobool(data) == 1

    @error_management
    def update_group(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.group = int(data)

    @error_management
    def update_thresold_presence(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.thresold_presence = int(data)

    @error_management
    def update_temperature_offset(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.temperature_offset = int(data)

    def run(self):
        self.connect()
        self.client.message_callback_add("/write/" + self.url_initial_setup, self.setup_configuration)
        self.client.message_callback_add("/write/" + self.url_brightness_correction_factor,
                                         self.update_brightness_correction_factor)
        self.client.message_callback_add("/write/" + self.url_is_configured, self.update_configuration_status)
        self.client.message_callback_add("/write/" + self.url_group, self.update_group)
        self.client.message_callback_add("/write/" + self.url_thresold_presence,
                                         self.update_thresold_presence)
        self.client.message_callback_add("/write/" + self.url_temperature_offset,
                                         self.update_temperature_offset)
        self.client.message_callback_add("/write/" + self.url_ble, self.enable_ble)
        while self.is_alive:
            if not self.is_configured:
                message = {
                    "mac": self.mac,
                    "type": "sensor",
                    "topic": self.base_topic
                }
                self.client.publish("/read/" + self.url_hello, json.dumps(message))
            else:
                if self.presence != self.old_presence:
                   # Start last_movement counts
                   self.last_movment = 0
                   self.old_presence = True
                if self.presence:
                   self.last_movment += 1
                if self.last_movment == self.thresold_presence:
                   # End detection
                   self.presence = False
                self.client.publish("/read/" + self.url_dump, json.dumps(self.serialize()))
            time.sleep(1)
        self.disconnect()
