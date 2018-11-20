#!/usr/bin/python3
# coding: utf-8

import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s %(levelname).3s %(filename)s:%(lineno)d - %(message)s', '%d/%m/%Y %H:%M:%S')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
