
import types
from . import channels, users, chat, rtm, auth

class Slack(object):

    def __init__(self, token):
        self.api = types.SimpleNamespace()
        self.api.channels = channels.ChannelsAPI(token)
        self.api.users = users.UsersAPI(token)
        self.api.chat = chat.ChatAPI(token)
        self.api.rtm = rtm.RealTimeMessagingAPI(token)
        self.api.auth = auth.AuthAPI(token)

