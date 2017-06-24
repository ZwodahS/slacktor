
import functools
from . import _GenericAPI
from .api_wrapper import RestAPI

_API = {
    "connect": {
        "url": "/api/rtm.connect",
        "method": "POST",
        "params": {
            "token": { "type": "string", "is_required": True },
        },
        "parse_data": ("url", "team", "self")
    },
}

class RealTimeMessagingAPI(_GenericAPI):

    def __init__(self, token):
        super().__init__(token, _API)

