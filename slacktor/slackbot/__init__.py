
import re
import uuid
import json
import types
import logging
import functools

import tornado.gen
import tornado.options
import tornado.httputil
import tornado.httpclient
import tornado.websocket

class SlackBot(object):

    def __init__(self, slack, http_client=None):
        self.slack = slack
        self.http_client = http_client or tornado.httpclient.AsyncHTTPClient()

        self.listeners = {}

    @tornado.gen.coroutine
    def _get_connection(self):
        connection = None
        tries = 0
        while connection is None and tries < 3:
            response = yield self.slack.api.rtm.connect()
            if response.code == 200 and response.data.ok:
                connection = yield tornado.websocket.websocket_connect(response.data.url)
                break
            tries += 1
        return connection

    @tornado.gen.coroutine
    def websocket_watch(self):
        """
        Watch for events using websocket
        """
        connection = yield self._get_connection()
        while connection:
            msg = yield connection.read_message()
            try:
                msg = json.loads(msg)
            except Exception as e:
                import traceback; traceback.print_exc()
                continue

            self._fire_event(None, msg)
            self._fire_event(msg["type"], msg)
            if msg["type"] == "goodbye":
                logging.info("Reconnecting")
                connection = yield self._get_connection()

    def _fire_event(self, event_name, event):
        handlers = self.listeners.get(event_name)
        if handlers:
            for handler in handlers.values():
                handler(event)

    def add_event_listener(self, event_name, func, name=None):
        name = name or uuid.uuid4()
        if event_name not in self.listeners:
            self.listeners[event_name] = {}

        self.listeners[event_name][name] = func
        return name

    def remove_event_listener(self, event_name, name):
        if event_name not in self.listeners:
            return None
        if name not in self.listeners[event_name]:
            return None
        return self.listeners[event_name].pop(name)

from . import extensions
from . import cache
