#!/usr/bin/python3
# coding: utf-8

import paho.mqtt.client as mqtt

from network.driver import Driver, error_management
import time
import json
from log import logger
from distutils.util import strtobool

class Blind(Driver):

    def __init__(self, broker_ip, mac, version):
        Driver.__init__(self, broker_ip, "blind/" + mac, mac, version)
        self.first_blind = 0
        self.second_blind = 0
        self.fin1 = "0"
        self.fin2 = "0"
        self.windows_status = False
        self.auto = False
        self.watchdog = 3600
        self.time_to_auto = 0
        self.is_daisy_chain_enabled = False
        self.daisy_chain_position = 0
        self.temperature = 0
        self.default_position = 1

        self.url_first_blind = self.url_base + "/blind1"
        self.url_second_blind = self.url_base + "/blind2"
        self.url_first_blind_manual = self.url_base + "/blind1Manual"
        self.url_second_blind_manual = self.url_base + "/blind2Manual"
        self.url_first_blind_fin_manual = self.url_base + "/fin1Manual"
        self.url_second_blind_fin_manual = self.url_base + "/fin2Manual"
        self.url_windows_status = self.url_base + "/windowStatus"
        self.url_version = self.url_config + "/version"
        self.url_is_configured = self.url_config + "/isConfigured"
        self.url_group = self.url_config + "/group"
        self.url_voltage_input = self.url_metric + "/voltageInput"
        self.url_time_to_auto = self.url_metric + "/timeToAuto"
        self.url_auto = self.url_status + "/auto"
        self.url_watchdog = self.url_config + "/watchdog"
        self.url_ble = self.url_config + "/isBleEnabled"
        self.url_daisy_enabled = self.url_config + "/isDaisyChainEnabled"
        self.url_daisy_position = self.url_config + "/daisyChainPosition"
        self.url_temperature = self.url_metric + "/temperature"
        self.url_time_to_auto = self.url_metric + "/timeToAuto"
        self.url_auto = self.url_status + "/auto"
        self.url_reset_numbers = self.url_metric + "/resetNumbers"
        self.url_initial_date = self.url_metric + "/initialSetupDate"
        self.url_last_reset = self.url_metric + "/lastResetDate"

    def serialize(self):
        blind = {
            "mac": self.mac,
            "isConfigured": self.is_configured,
            "error": self.error,
            "initialSetupDate": self.initial_date
        }
        if self.is_configured:
            blind["group"] = self.group
            blind["version"] = self.version
            blind["resetNumbers"] = self.reset_numbers
            blind["lastResetDate"] = self.last_reset_date
            blind["auto"] = self.auto
            blind["isBleEnabled"] = self.is_ble_enabled
            blind["isDaisyChainEnabled"] = self.is_daisy_chain_enabled
            blind["daisyChainPosition"] = self.daisy_chain_position
            blind["voltageInput"] = self.voltage_input
            blind["temperature"] = self.temperature
            blind["timeToAuto"] = self.time_to_auto
            blind["watchdog"] = self.watchdog
            if self.auto:
                blind["blind1"] = self.first_blind
                blind["blind2"] = self.second_blind
            else:
                blind["blind1Manual"] = self.first_blind
                blind["blind2Manual"] = self.second_blind
                blind["fin1Manual"] = self.fin1
                blind["fin2Manual"] = self.fin2
        return blind

    @error_management
    def setup_configuration(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        config = json.loads(data)
        logger.info("Not yet implemented setup_configuration for blind %r", config)
        self.is_configured = True

    @error_management
    def update_first_blind(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info("Auto update first blind auto?:%r with %r", self.auto, data)
        if not self.auto:
            return
        self.first_blind = int(data)

    @error_management
    def update_first_blind_manual(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info("Manual update first blind auto?:%r with %r", self.auto, data)
        if self.auto:
            return
        self.first_blind = int(data)

    @error_management
    def update_second_blind(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info("Auto update second blind auto?:%r with %r", self.auto, data)
        if not self.auto:
            return
        self.second_blind = int(data)

    @error_management
    def update_second_blind_manual(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info("Manual update second blind auto?:%r with %r", self.auto, data)
        if self.auto:
            return
        self.second_blind = int(data)

    @error_management
    def update_configuration_status(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        # Field used for reset to default
        self.is_configured = strtobool(data) == 1
        self.reset_numbers += 1
        self.last_reset_date = time.time()

    @error_management
    def update_group(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.group = int(data)

    @error_management
    def update_watchdog(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.watchdog = int(data)

    @error_management
    def enable_ble(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.is_ble_enabled = strtobool(data) == 1

    def switch_fin(self, orientation, blind):
        logger.info("Change fin orientation to %r", orientation)

    @error_management
    def update_fin1_manual(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        if self.auto:
            return
        self.switch_fin(data, 1)

    @error_management
    def update_fin2_manual(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        if self.auto:
            return
        self.switch_fin(data, 2)

    @error_management
    def update_auto_mode(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        self.auto = strtobool(data) == 1
        logger.info("Received switch mode to %r: %r", data, self.auto)
        if self.auto:
            #  Switch in automatic mode (manage by group)
            self.time_to_auto = 0
            logger.info("Switch to automatic mode")
        else:
            # Switch in manual mode
            self.time_to_auto = self.watchdog
            logger.info("Switch to manual mode, start timer to %r", self.time_to_auto)

    def run(self):
        self.connect()
        self.client.message_callback_add("/write/" + self.url_initial_setup, self.setup_configuration)
        self.client.message_callback_add("/write/" + self.url_watchdog, self.update_watchdog)
        self.client.message_callback_add("/write/" + self.url_auto, self.update_auto_mode)
        self.client.message_callback_add("/write/" + self.url_first_blind,
                                         self.update_first_blind)
        self.client.message_callback_add("/write/" + self.url_first_blind_manual,
                                         self.update_first_blind_manual)
        self.client.message_callback_add("/write/" + self.url_second_blind,
                                         self.update_second_blind)
        self.client.message_callback_add("/write/" + self.url_second_blind_manual,
                                         self.update_second_blind_manual)
        self.client.message_callback_add("/write/" + self.url_group, self.update_group)
        self.client.message_callback_add("/write/" + self.url_ble, self.enable_ble)
        self.client.message_callback_add("/write/" + self.url_is_configured, self.update_configuration_status)
        self.client.message_callback_add("/write/" + self.url_first_blind_fin_manual, self.update_fin1_manual)
        self.client.message_callback_add("/write/" + self.url_second_blind_fin_manual, self.update_fin2_manual)
        while self.is_alive:
            if not self.is_configured:
                message = {
                    "mac": self.mac,
                    "type": "sensor",
                    "topic": self.base_topic
                }
                self.client.publish("/read/" + self.url_hello, json.dumps(message))
            else:
                if self.time_to_auto <= 0:
                    # Switch back to automatic mode
                    self.auto = True
                    logger.info("Switch %r back to automatic mode", self.mac)
                if self.time_to_auto:
                    self.time_to_auto -= 1
                self.client.publish("/read/" + self.url_dump, json.dumps(self.serialize()))
            time.sleep(1)
        self.disconnect()
