
import re
import json
import types
import functools

import tornado.gen
import tornado.httpclient
from .api_wrapper import RestAPI

URL_PARAMS_REGEX = re.compile("(\{.*?\})")

class _GenericAPI(object):

    def __init__(self, token, api_definitions, http_client=None):
        self.token = token
        self.http_client = http_client or tornado.httpclient.AsyncHTTPClient()

        for function_name, definition in api_definitions.items():
            definition["host"] = "slack.com" if "host" not in definition else definition["host"]
            definition["protocol"] = "https" if "protocol" not in definition else definition["protocol"]
            parse_data = definition.pop("parse_data", None)
            definition = (RestAPI.from_config(definition)
                .set(decode="utf-8").partial(token=self.token))
            if parse_data is not None:
                definition.add_post_response_hook(hooks=functools.partial(
                    self._post_response, parse_data=parse_data))
            setattr(self, function_name, definition)

    def _post_response(self, response, parse_data=None):
        if parse_data is not None and not isinstance(parse_data, (list, set, tuple)):
            parse_data = list(parse_data)

        try:
            response.json_body = json.loads(response.body.decode("utf-8"))
            if parse_data is not None:
                response.data = types.SimpleNamespace()
                response.data.ok = response.json_body["ok"]
                response.data.error = response.json_body.get("error")
                if response.data.ok:
                    for key in parse_data:
                        setattr(response.data, key, response.json_body.get(key))

        except Exception as e:
            import traceback; traceback.print_exc()
            response.json_body = None
            response.ok = False

        return False


from . import slack
from . import slackbot
