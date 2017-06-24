
import functools
from . import _GenericAPI
from .api_wrapper import RestAPI

_API = {
    "list": {
        "url": "/api/channels.list",
        "method": "GET",
        "params": {
            "token": { "type": "string", "is_required": True },
            "exclude_archived": { "type": "bool_string" },
            "exclude_members": { "type": "bool_string" },
        },
        "parse_data": ("channels", )
    },
    "history": {
        "url": "/api/channels.history",
        "method": "GET",
        "params": {
            "token": { "type": "string", "is_required": True },
            "channel": { "type": "string", "is_required": True },
            "latest": { "type": "float" },
            "oldest": { "type": "float" },
            "inclusive": { "type": "bool_string" },
            "count": { "type": "int" },
            "unreads": { "type": "bool_string" },
        }
    }
}
class ChannelsAPI(_GenericAPI):

    def __init__(self, token):
        super().__init__(token, _API)
