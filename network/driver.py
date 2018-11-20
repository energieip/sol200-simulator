#!/usr/bin/python3
# coding: utf-8

import paho.mqtt.client as mqtt
from threading import Thread
import paho.mqtt.subscribe as subscribe
from log import logger
import time

def error_management(func):
    def func_wrapper(*args, **kwargs):
        try:
            logger.info("Call %r", func.__name__)
            return func(*args, **kwargs)
        except:
            logger.exception("Invalid value received")
    return func_wrapper


class Driver(Thread):

    def __init__(self, broker_ip, base_topic, mac, version):
        Thread.__init__(self)
        self.version = version
        self.mac = mac
        self.broker_ip = broker_ip
        self.base_topic = base_topic
        self.is_configured = False
        self.is_ble_enabled = False
        self.reset_numbers = 0
        self.initial_date = time.time()
        self.last_reset_date = 0
        self.error = 0
        self.voltage_input = 36
        self.group = 0

        self.url_base = self.base_topic + "/base"
        self.url_config = self.base_topic + "/config"
        self.url_metric = self.base_topic + "/metric"
        self.url_status = self.base_topic + "/status"
        self.url_error = self.url_status + "/error"
        self.url_ping = self.url_status + "/ping"
        self.url_setup = self.base_topic + "/setup"
        self.url_hello = self.url_setup + "/hello"
        self.url_initial_setup = self.url_setup + "/config"
        self.url_dump = self.url_status + "/dump"

    def event_received(self, client, userdata, message):
        data = message.payload.decode("utf-8")
        logger.info("received url %r %r", message.topic, str(data))

    def event_publish(self, client, userdata, result):
        pass

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Unexpected client disconnect for %r, will reconnect")

    def connect(self):
        self.client = mqtt.Client(self.mac)
        self.client.on_message = self.event_received
        self.client.on_publish = self.event_publish
        self.client.on_disconnect = self.on_disconnect
        self.client.connect(self.broker_ip)
        self.client.loop_start()
        self.client.subscribe("/write/" + self.base_topic + "/#")

    def disconnect(self):
        self.client.loop_stop()

    def run(self):
        pass