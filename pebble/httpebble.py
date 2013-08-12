#!/usr/bin/env python

import logging

log = logging.getLogger()
logging.basicConfig(format='[%(levelname)-8s] %(message)s')
log.setLevel(logging.DEBUG)

import bridge, uuid, json, urllib2

from struct import pack, unpack

from pebble import AppMessage

class HTTPebble(bridge.PebbleBridge):
	UUID = uuid.UUID(bytes="\x91\x41\xB6\x28\xBC\x89\x49\x8E\xB1\x47\x04\x9F\x49\xC0\x99\xAD")

	type_conversion = {
		'b': ('INT', 'b'),
		'B': ('UINT', 'B'),
		's': ('INT', 'h'),
		'S': ('UINT', 'H'),
		'i': ('INT', 'i'),
		'I': ('UINT', 'I')
	}

	def http_url_key(self, uri, parameters):
		cookie = parameters['HTTP_COOKIE_KEY']
		app_id = parameters['HTTP_APP_ID_KEY']
		del parameters['HTTP_COOKIE_KEY']
		del parameters['HTTP_APP_ID_KEY']

		log.info(uri)

		log.info(json.dumps(parameters))

		req = urllib2.Request(uri)
		req.add_header('Content-Type', 'application/json')
		req.add_header('X-Pebble-ID', self._id)
		response = urllib2.urlopen(req, json.dumps(parameters))

		code = response.getcode()
		data = json.load(response)

		log.info("%d: %s" % (code, data))

		vals = [
			(0xFFFE, "UINT", pack("<H", code)),
			(0xFFFF, "UINT", pack("<B", (1 if code is 200 else 0))),
			(0xFFFC, "UINT", pack("<I", cookie)),
			(0xFFF2, "UINT", pack("<I", app_id))
		]



		for k in data:
			v = data[k]
			k = int(k)
			if type(v) is list:
				assert len(v) == 2
				t = v[0]
				v = v[1]

				assert t in self.type_conversion
				t = self.type_conversion[t]
				vals.append((k, t[0], pack('<%s' % t[1], v)))
			elif type(v) is int:
				vals.append((k, "INT", pack('<i', v)))
			else:
				vals.append((k, "CSTRING", v))

		tuples = [AppMessage.construct_tuple(*x) for x in vals]
		return AppMessage.construct_dict(tuples)


	def http_location_key(self, code, parameters):
		assert code == 1, "Expected 1, got %s" % repr(code)
		assert len(parameters) == 0
		vals = [
			(0xFFE0, 5.0),
			(0xFFE1, 47.62052),
			(0xFFE2, -122.32408),
			(0xFFE3, 31.337),
		]
		tuples = [AppMessage.construct_tuple(x[0], "UINT", pack("<f", x[1])) for x in vals]
		return AppMessage.construct_dict(tuples)


	def http_time_key(self, code, parameters):
		pass

	def http_cookie_store(self, code, parameters):
		pass

	def http_cookie_load(self, code, parameters):
		pass

	def http_cookie_fsync(self, code, parameters):
		pass

	def http_cookie_delete(self, code, parameters):
		pass

	commands = {
		0xFFFF: http_url_key, #HTTP_URL_KEY
		0xFFE0: http_location_key, #HTTP_LOCATION_KEY
		0xFFF5: http_time_key, #HTTP_TIME_KEY
		0xFFF0: http_cookie_store, #HTTP_COOKIE_STORE_KEY
		0xFFF1: http_cookie_load, #HTTP_COOKIE_LOAD_KEY
		0xFFF3: http_cookie_fsync, #HTTP_COOKIE_FSYNC_KEY
		0xFFF4: http_cookie_delete, #HTTP_COOKIE_DELETE_KEY
	}

	other_keys = {
		0xFFFE: 'HTTP_STATUS_KEY', #HTTP_STATUS_KEY
		0xFFFC: 'HTTP_COOKIE_KEY', #HTTP_COOKIE_KEY
		0xFFFB: 'HTTP_CONNECT_KEY', #HTTP_CONNECT_KEY
		0xFFFA: 'HTTP_USE_GET_KEY', #HTTP_USE_GET_KEY
		0xFFF2: 'HTTP_APP_ID_KEY', #HTTP_APP_ID_KEY
		0xFFF6: 'HTTP_UTC_OFFSET_KEY', #HTTP_UTC_OFFSET_KEY
		0xFFF7: 'HTTP_IS_DST_KEY', #HTTP_IS_DST_KEY
		0xFFF8: 'HTTP_TZ_NAME_KEY', #HTTP_TZ_NAME_KEY
		0xFFE1: 'HTTP_LATITUDE_KEY', #HTTP_LATITUDE_KEY
		0xFFE2: 'HTTP_LONGITUDE_KEY', #HTTP_LONGITUDE_KEY
		0xFFE3: 'HTTP_ALTITUDE_KEY', #HTTP_ALTITUDE_KEY
	}

	def __init__(self, pebble):
		self._pebble = pebble
		self._id = pebble.id
		if len(self._id) > 4:
			self._id = self._id[-5:-3] + self._id[-2:] #TODO: Verify


	def process(self, msg_dict):
		parameters = {}
		command = None
		code = None
		for k in msg_dict:
			if k in self.other_keys:
				parameters[self.other_keys[k]] = msg_dict[k]
			elif k in self.commands:
				c = self.commands[k]
				if command is not None:
					log.error("Got more than one command; %s" % c)
				else:
					log.info("HTTP command: %s" % c)
					command = c
					code = msg_dict[k]
			else:
				parameters[k] = msg_dict[k]

		for p in parameters:
			log.info("    %s: %s" % (p, repr(parameters[p])))

		return command(self, code, parameters)

