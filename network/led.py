#!/usr/bin/python3
# coding: utf-8

import paho.mqtt.client as mqtt

from network.driver import Driver, error_management
import time
import json
from log import logger

from distutils.util import strtobool

class Led(Driver):

    def __init__(self, broker_ip, mac, version):
        Driver.__init__(self, broker_ip, "led/" + mac, mac, version)
        self.brightness = 0
        self.watchdog = 3600
        self.i_max = 0
        self.temperature = 0
        self.thresold_low = 10
        self.thresold_high = 100
        self.is_daisy_chain_enabled = False
        self.daisy_chain_position = 0
        self.device_power = 0
        self.energy = 0
        self.voltage_led = 0
        self.line_power = 0
        self.duration = 0
        # temp variable for duration
        self.duration_seconds = 0
        self.time_to_auto = 0
        self.auto = False
        self.default_brightness = 20 #default value when the switch is not responding

        self.url_setpoint = self.url_base + "/setpoint"
        self.url_setpoint_manual = self.url_base + "/setpointManual"
        self.url_version = self.url_config + "/version"
        self.url_is_configured = self.url_config + "/isConfigured"
        self.url_watchdog = self.url_config + "/watchdog"
        self.url_i_max = self.url_config + "/iMax"
        self.url_group = self.url_config + "/group"
        self.url_thresold_low = self.url_config + "/thresoldLow"
        self.url_thresold_high = self.url_config + "/thresoldHigh"
        self.url_ble = self.url_config + "/isBleEnabled"
        self.url_daisy_enabled = self.url_config + "/isDaisyChainEnabled"
        self.url_daisy_position = self.url_config + "/daisyChainPosition"
        self.url_device_power = self.url_metric + "/devicePower"
        self.url_energy = self.url_metric + "/energy"
        self.url_voltage_led = self.url_metric + "/voltageLed"
        self.url_voltage_input = self.url_metric + "/voltageInput"
        self.url_temperature = self.url_metric + "/temperature"
        self.url_line_power = self.url_metric + "/linePower"
        self.url_duration = self.url_metric + "/duration"
        self.url_time_to_auto = self.url_metric + "/timeToAuto"
        self.url_auto = self.url_status + "/auto"
        self.url_reset_numbers = self.url_metric + "/resetNumbers"
        self.url_initial_date = self.url_metric + "/initialSetupDate"
        self.url_last_reset = self.url_metric + "/lastResetDate"


    def serialize(self):
        led = {
            "mac": self.mac,
            "isConfigured": self.is_configured,
            "error": self.error,
            "initialSetupDate": self.initial_date
        }
        if self.is_configured:
            led["duration"] = self.duration
            led["version"] = self.version
            led["brightness"] = self.brightness
            led["watchdog"] = self.watchdog
            led["iMax"] = self.i_max
            led["group"] = self.group
            led["thresoldLow"] = self.thresold_low
            led["thresoldHigh"] = self.thresold_high
            led["isBleEnabled"] = self.is_ble_enabled
            led["isDaisyChainEnabled"] = self.is_daisy_chain_enabled
            led["daisyChainPosition"] = self.daisy_chain_position
            led["devicePower"] = self.device_power
            led["energy"] = self.energy
            led["voltageLed"] = self.voltage_led
            led["voltageInput"] = self.voltage_input
            led["temperature"] = self.temperature
            led["linePower"] = self.line_power
            led["timeToAuto"] = self.time_to_auto
            led["auto"] = self.auto
            led["resetNumbers"] = self.reset_numbers
            led["lastResetDate"] = self.last_reset_date
            led["defaultBrigthness"] = self.default_brightness
        return led

    @error_management
    def update_auto_mode(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        old_state = self.auto
        self.auto = strtobool(data) == 1
        if self.auto == old_state:
            return
        if self.auto:
            #  Switch in automatic mode (manage by group)
            self.time_to_auto = 0
            logger.info("Switch to automatic mode")
        else:
            # Switch in manual mode
            self.time_to_auto = self.watchdog
            logger.info("Switch to manual mode, start timer to %r", self.time_to_auto)

    @error_management
    def update_watchdog(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.watchdog = int(data)

    @error_management
    def update_group(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.group = int(data)

    @error_management
    def setup_configuration(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        config = json.loads(data)
        self.i_max = config["iMax"]
        self.group = config.get("group", self.group)
        self.thresold_low = config.get("thresoldLow", self.thresold_low)
        self.thresold_high = config.get("thresoldHigh", self.thresold_high)
        self.default_brightness = config.get("defaultBrightness", self.default_brightness)
        self.is_configured = True

    @error_management
    def update_configuration_status(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        # Field used for reset to default
        self.is_configured = strtobool(data) == 1
        self.reset_numbers += 1
        self.last_reset_date = time.time()

    @error_management
    def update_thresold_high(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.thresold_high = int(data)

    @error_management
    def update_thresold_low(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.thresold_low = int(data)

    @error_management
    def enable_ble(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.is_ble_enabled = strtobool(data) == 1

    @error_management
    def update_brigthness_auto(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info('Received auto order to update brigthness auto? %r: %r', self.auto, data)
        if not self.auto:
            return
        self.set_brigthness(int(data))

    @error_management
    def update_brigthness_manual(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info('Received manual order to update brigthness auto? %r: %r', self.auto, data)
        if self.auto:
            return
        self.set_brigthness(int(data))

    def set_brigthness(self, new_brigthness):
        if new_brigthness > self.thresold_high:
            new_brigthness = self.thresold_high
        if new_brigthness < 0:
            new_brigthness = 0
        if new_brigthness and new_brigthness < self.thresold_low:
            new_brigthness = 0
        self.brightness = new_brigthness
        logger.info("LED %r has now %r", self.mac, self.brightness)

    def run(self):
        self.connect()
        self.client.message_callback_add("/write/" + self.url_auto, self.update_auto_mode)
        self.client.message_callback_add("/write/" + self.url_watchdog, self.update_watchdog)
        self.client.message_callback_add("/write/" + self.url_group, self.update_group)
        self.client.message_callback_add("/write/" + self.url_initial_setup, self.setup_configuration)
        self.client.message_callback_add("/write/" + self.url_is_configured, self.update_configuration_status)
        self.client.message_callback_add("/write/" + self.url_thresold_high, self.update_thresold_high)
        self.client.message_callback_add("/write/" + self.url_thresold_low, self.update_thresold_low)
        self.client.message_callback_add("/write/" + self.url_ble, self.enable_ble)
        self.client.message_callback_add("/write/" + self.url_setpoint, self.update_brigthness_auto)
        self.client.message_callback_add("/write/" + self.url_setpoint_manual, self.update_brigthness_manual)
        while self.is_alive:
            if not self.is_configured:
                message = {
                    "mac": self.mac,
                    "type": "led",
                    "topic": self.base_topic
                }
                self.client.publish("/read/" + self.url_hello, json.dumps(message))
            else:
                if self.brightness:
                    self.duration_seconds += 1
                if self.duration_seconds == 3600:
                    self.duration += 1
                    self.duration_seconds = 0

                if self.time_to_auto <= 0:
                    # Switch back to automatic mode
                    self.auto = True
                    logger.info("Switch %r back to automatic mode", self.mac)
                if self.time_to_auto:
                    self.time_to_auto -= 1
                self.client.publish("/read/" + self.url_dump, json.dumps(self.serialize()))
            time.sleep(1)
        self.disconnect()
