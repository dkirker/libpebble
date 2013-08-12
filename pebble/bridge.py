#!/usr/bin/env python

import logging

log = logging.getLogger()
logging.basicConfig(format='[%(levelname)-8s] %(message)s')
log.setLevel(logging.DEBUG)

class PebbleBridge(object):
	def __init__(self, pebble):
		self._pebble = pebble

	def process(self, data):
		log.debug("DATA: %s", repr(data))