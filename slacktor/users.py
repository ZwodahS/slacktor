
import functools
from . import _GenericAPI
from .api_wrapper import RestAPI

_API = {
    "list": {
        "url": "/api/users.list",
        "method": "GET",
        "params": {
            "token": { "type": "string", "is_required": True },
            "presence": { "type": "bool_string" },
        },
        "parse_data": ("members", )
    },
}
class UsersAPI(_GenericAPI):

    def __init__(self, token):
        super().__init__(token, _API)
