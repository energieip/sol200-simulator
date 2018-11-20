#!/usr/bin/python3

import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.append('/var/www/websimulator')
from websimulator import app as application

