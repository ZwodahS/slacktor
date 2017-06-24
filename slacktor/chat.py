
import functools
from . import _GenericAPI
from .api_wrapper import RestAPI

_API = {
    "post_message": {
        "url": "/api/chat.postMessage",
        "method": "POST",
        "params": {
            "token": { "type": "string", "is_required": True },
            "channel": { "type": "string", "is_required": True },
            "text": { "type": "string" },
            "attachments": { "type": "list" },
            "as_user": { "type": "bool" },
            "thread_ts": { "type": "float" },
            "parse": { "type": "string" },
            # other params added if necessary
        },
        "parse_data": ("url", "team", "self")
    },
}

class ChatAPI(_GenericAPI):

    def __init__(self, token):
        super().__init__(token, _API)
