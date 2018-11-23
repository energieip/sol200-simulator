#!/usr/bin/python3
# coding: utf-8

import sys
import time

from network.led import Led
from network.switch import Switch
from network.sensor import Sensor
from network.blind import Blind

from flask import Flask, jsonify, request
from flasgger import Swagger
from flasgger.utils import swag_from

import string
import random
from log import logger
import argparse

try:
    from http import HTTPStatus
except ImportError:
    import http.client as HTTPStatus

def mac_generator(size=12, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

app = Flask(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--broker",  type=str, default="127.0.0.1",
                        help="Broker ip address by default 127.0.0.1")
    parser.add_argument("-p", "--port",  type=str, default="80",
                        help="web port by default 80")
    args = parser.parse_args()
    logger.info("Broker address is %r", args.broker)
    broker_address = args.broker
    port = args.port

    logger.info("EnergieIP Simulator")

    switch = Switch(broker_address)
    switch.start()

    swagger_config = {
        'headers': [
            ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'),
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'SAMEORIGIN'),
            ('X-XSS-Protection', '1; mode=block')
        ],
        'specs': [
            {
                'endpoint': 'apispec',
                'route': '/apispec.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        'swagger_ui': True,
        "specs_route": "/"
    }
    Swagger(app,  template_file='swagger/api.json', config=swagger_config)

    @app.route('/v1/led/new', methods=['POST'])
    def led_new():
        mac = mac_generator()
        while switch.get_led(mac):
            mac = mac_generator()
        led = Led(broker_address, mac, 2.3)
        switch.plug_led(led)
        led.start()
        return jsonify(led.serialize()), HTTPStatus.OK

    @app.route('/v1/led/brightness', methods=['POST'])
    def led_brightness():
        mac = request.json["mac"]
        led = switch.get_led(mac)
        if not led:
            error = {
                "Message": "Unknow led " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        if not led.is_configured:
            error = {
                "Message": "Led setup is not finish; please wait"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        setpoint = request.json["setpoint"]
        switch.set_manual_led_brightness(mac, setpoint)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/led/switchMode', methods=['POST'])
    def switch_mode_led():
        mac = request.json["mac"]
        led = switch.get_led(mac)
        if not led:
            error = {
                "Message": "Unknow led " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        if not led.is_configured:
            error = {
                "Message": "Led setup is not finish; please wait"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        mode = request.json["auto"]
        switch.switch_led_mode(mac, mode)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/sensor/new', methods=['POST'])
    def sensor_new():
        mac = mac_generator()
        while switch.get_sensor(mac):
            mac = mac_generator()
        sensor = Sensor(broker_address, mac, 2.3)
        switch.plug_sensor(sensor)
        sensor.start()
        return jsonify(sensor.serialize()), HTTPStatus.OK

    @app.route('/v1/blind/new', methods=['POST'])
    def blind_new():
        mac = mac_generator()
        while switch.get_sensor(mac):
            mac = mac_generator()
        blind = Blind(broker_address, mac, 3.1)
        switch.plug_blind(blind)
        blind.start()
        return jsonify(blind.serialize()), HTTPStatus.OK

    @app.route('/v1/blind/switchMode', methods=['POST'])
    def switch_mode_blind():
        mac = request.json["mac"]
        blind = switch.get_blind(mac)
        if not blind:
            error = {
                "Message": "Unknow blind " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST

        if not blind.is_configured:
            error = {
                "Message": "Led setup is not finish; please wait"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        mode = request.json["auto"]
        switch.switch_blind_mode(mac, mode)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/blind/position', methods=['POST'])
    def blind_postion():
        mac = request.json["mac"]
        blind = switch.get_blind(mac)
        if not blind:
            error = {
                "Message": "Unknow blind " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        if not blind.is_configured:
            error = {
                "Message": "Blind setup is not finish; please wait"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        position = request.json["position"]
        if position not in [0, 1, 2]:
            error = {
                "Message": "Blind position must be in [0, 1, 2]"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        blinds = request.json.get("blindNumber", 0)
        if blinds not in [0, 1, 2]:
            error = {
                "Message": "Blind number must be in [0, 1, 2]"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        switch.set_manual_blind_position(mac, position, blinds)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/blind/fin', methods=['POST'])
    def blind_fin():
        mac = request.json["mac"]
        blind = switch.get_blind(mac)
        if not blind:
            error = {
                "Message": "Unknow blind " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        if not blind.is_configured:
            error = {
                "Message": "Blind setup is not finish; please wait"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        fin = request.json["fin"]
        if fin not in ["0", "+45", "-45", "-90", "+90"]:
            error = {
                "Message": "Blind position must be in [0, +45, -45, +90, -90]"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        blinds = request.json.get("blindNumber", 0)
        if blinds not in [0, 1, 2]:
            error = {
                "Message": "Blind number must be in [0, 1, 2]"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        # switch.set_manual_blind_fin(mac, fin, blinds)
        # return jsonify(), HTTPStatus.OK
        error = {
                "Message": "Not yet Implemented"
            }
        return jsonify(error), HTTPStatus.BAD_REQUEST

    @app.route('/v1/debug/sensor/brightnessRaw', methods=['POST'])
    def debug_sensor_brightness():
        mac = request.json["mac"]
        sensor = switch.get_sensor(mac)
        if not sensor:
            error = {
                "Message": "Unknow sensor " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        brightness = request.json["brightness"]
        sensor.brightness_raw = brightness
        return jsonify(sensor.serialize()), HTTPStatus.OK

    @app.route('/v1/debug/sensor/presence', methods=['POST'])
    def debug_sensor_presence():
        mac = request.json["mac"]
        sensor = switch.get_sensor(mac)
        if not sensor:
            error = {
                "Message": "Unknow sensor " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        sensor.presence = request.json["presence"]
        return jsonify(sensor.serialize()), HTTPStatus.OK

    @app.route('/v1/debug/sensor/temperatureRaw', methods=['POST'])
    def debug_sensor_temperature():
        mac = request.json["mac"]
        sensor = switch.get_sensor(mac)
        if not sensor:
            error = {
                "Message": "Unknow sensor " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        temperature = request.json["temperature"]
        sensor.temperature_raw = temperature
        return jsonify(sensor.serialize()), HTTPStatus.OK

    @app.route('/v1/group/new', methods=['POST'])
    def group_new():
        group_id = request.json["group"]
        if group_id < 1:
            error = {
                "Message": "Group must be greater than 0 (0 = default group)"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        driver_leds = []
        network_sensors = []
        driver_blinds = []
        for led in request.json.get("leds", []):
            light = switch.get_led(led)
            if not light:
                error = {
                    "Message": "Unknow led " + led
                }
                return jsonify(error), HTTPStatus.BAD_REQUEST
            if light.group != 0:
                error = {
                    "Message": "led " + led + "already associate to a group"
                }
                return jsonify(error), HTTPStatus.BAD_REQUEST
            driver_leds.append(light)
        for sensor in request.json.get("sensors", []):
            s = switch.get_sensor(sensor)
            if not s:
                error = {
                    "Message": "Unknow sensor " + sensor
                }
                return jsonify(error), HTTPStatus.BAD_REQUEST

            if s.group != 0:
                error = {
                    "Message": "Sensor " + sensor + "already associate to a group"
                }
                return jsonify(error), HTTPStatus.BAD_REQUEST
            network_sensors.append(s)

        for blind in request.json.get("blinds", []):
            s = switch.get_blind(blind)
            if not s:
                error = {
                    "Message": "Unknow blind " + blind
                }
                return jsonify(error), HTTPStatus.BAD_REQUEST
            if s.group != 0:
                error = {
                    "Message": "blind " + blind + "already associate to a group"
                }
                return jsonify(error), HTTPStatus.BAD_REQUEST
            driver_blinds.append(s)

        resp = switch.create_group(driver_leds, network_sensors, driver_blinds, group_id)
        if resp:
            presence = request.json.get("presence", 600)
            switch.update_group_rules(group_id, "presence", presence)
            temperature = request.json.get("temperature", 200)
            switch.update_group_rules(group_id, "temperature", temperature)
            brightness = request.json.get("brightness", 300)
            switch.update_group_rules(group_id, "brightness", brightness)
            return jsonify(switch.get_group_id(group_id).serialize()), HTTPStatus.OK
        error = {
            "Message": "Goup " + str(group_id) + " already exists"
        }
        return jsonify(error), HTTPStatus.BAD_REQUEST

    @app.route('/v1/group/add', methods=['POST'])
    def group_add():
        group_id = request.json["group"]
        if group_id < 1:
            error = {
                "Message": "Group must be greater than 0"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        mac = request.json["mac"]
        led = switch.get_led(mac)
        sensor = switch.get_sensor(mac)
        blind = switch.get_blind(mac)
        if not led and not sensor and not blind:
            error = {
                "Message": "Unknow driver " + mac
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        if (led and led.group != 0) or (blind and blind.group != 0) or (sensor and sensor.group != 0):
            error = {
                "Message": "Driver " + mac + " already associate to a group"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        driver_type = ""
        if sensor:
            driver_type = "sensor"
        elif led:
            driver_type = "led"
        elif blind:
            driver_type = "blind"
        resp = switch.add_driver_to_group(group_id, driver_type, mac)
        if resp:
            return jsonify(switch.get_group_id(group_id).serialize()), HTTPStatus.OK
        error = {
            "Message": "Driver " + mac + " cannot be added to group " + str(group_id)
        }
        return jsonify(error), HTTPStatus.BAD_REQUEST

    @app.route('/v1/group/rules/brightness', methods=['POST'])
    def group_brightness():
        group_id = request.json["group"]
        brightness = request.json.get("brightness", 300)
        resp = switch.update_group_rules(group_id, "brightness", brightness)
        if resp:
            return jsonify(switch.get_group_id(group_id).serialize()), HTTPStatus.OK
        error = {
            "Message": "Unknow Group " + str(group_id)
        }
        return jsonify(error), HTTPStatus.BAD_REQUEST

    @app.route('/v1/group/rules/presence', methods=['POST'])
    def group_presence():
        group_id = request.json["group"]
        presence = request.json.get("presence", 600)
        resp = switch.update_group_rules(group_id, "presence", presence)
        if resp:
            return jsonify(switch.get_group_id(group_id).serialize()), HTTPStatus.OK
        error = {
            "Message": "Unknow Group " + str(group_id)
        }
        return jsonify(error), HTTPStatus.BAD_REQUEST

    @app.route('/v1/group/rules/temperature', methods=['POST'])
    def group_temperature():
        group_id = request.json["group"]
        temperature = request.json.get("temperature", 200)
        resp = switch.update_group_rules(group_id, "temperature", temperature)
        if resp:
            return jsonify(switch.get_group_id(group_id).serialize()), HTTPStatus.OK
        error = {
            "Message": "Unknow Group " + str(group_id)
        }
        return jsonify(error), HTTPStatus.BAD_REQUEST

    @app.route('/v1/group/switchMode', methods=['POST'])
    def switch_mode_group():
        group_id = request.json["group"]
        group = switch.get_group_id(group_id)
        if not group:
            error = {
                "Message": "Unknow group " + group_id
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        mode = request.json["auto"]
        switch.switch_group_mode(group_id, mode)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/group/blindPosition', methods=['POST'])
    def group_blind_postion():
        group_id = request.json["group"]
        group = switch.get_group_id(group_id)
        if not group:
            error = {
                "Message": "Unknow group " + group_id
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        position = request.json["position"]
        if position not in [0, 1, 2]:
            error = {
                "Message": "Blind position must be in [0, 1, 2]"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        switch.set_group_blind_position(group_id, position)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/group/setpoint', methods=['POST'])
    def group_led_setpoint():
        group_id = request.json["group"]
        group = switch.get_group_id(group_id)
        if not group:
            error = {
                "Message": "Unknow group " + group_id
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        setpoint = request.json["setpoint"]
        if setpoint > 100 or setpoint < 0:
            error = {
                "Message": "Setpoint value must be between 0 and 100 %"
            }
            return jsonify(error), HTTPStatus.BAD_REQUEST
        switch.set_group_setpoint(group_id, setpoint)
        return jsonify(), HTTPStatus.OK

    @app.route('/v1/switch', methods=['GET'])
    def list_drivers():
        sensors = switch.list_sensors()
        leds = switch.list_leds()
        blinds = switch.list_blinds()
        groups = switch.list_groups()
        return jsonify(leds=[led.serialize() for led in leds],
                       sensors=[sensor.serialize() for sensor in sensors],
                       blinds=[blind.serialize() for blind in blinds],
                       groups=[group.serialize() for group in groups]), HTTPStatus.OK

    @app.route('/v1/switch/diagnostic', methods=['GET'])
    def generate_diagnostic():
        diag = switch.get_diagnostic()
        return jsonify(config=diag["config"], events=diag['events']), HTTPStatus.OK

    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    sys.exit(main())