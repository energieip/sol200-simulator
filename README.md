WebAPI simulator
================

The simulator is responsible for:
* offering swagger API
* simulating drivers objects (e.g.: sensor, LED, Blind)
* simulating group behaviour
* sending manual command to group and driver elements
* simulate network command on MQTT


To install it:
```
$ sudo apt-get install python3-pip python3-httplib2 mosquitto
$ sudo pip3 install paho-mqtt
$ sudo pip3 install Flask
$ sudo pip3 install flasgger
$ sudo pip3 install pyopenssl
```

A MQTT broker is necessary: mosquitto

Website url for flasgger(rest api): http://127.0.0.1/

When you install it, on your pc, please specifiy the broker address. By default, it will be 127.0.0.1

To execute it:
```
./websimulator.py
```

To Get the user manual: 
```
./websimulator.py -h
```
