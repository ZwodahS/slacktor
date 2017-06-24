
import functools
from . import _GenericAPI
from .api_wrapper import RestAPI

_API = {
    "test": {
        "url": "/api/auth.test",
        "method": "GET",
        "params": {
            "token": { "type": "string", "is_required": True },
        },
        "parse_data": ("url", "team", "user", "team_id", "user_id")
    },
}

class AuthAPI(_GenericAPI):

    def __init__(self, token):
        super().__init__(token, _API)
