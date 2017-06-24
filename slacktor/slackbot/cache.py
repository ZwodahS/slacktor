
import tornado.gen

class Cache(object):

    def __init__(self, slack):
        self.slack = slack
        self.channel_name_to_id = {}
        self.channel_is_in = set()
        self.channel_id_to_name = {}
        self.user_name_to_id = {}
        self.user_id_to_name = {}

    def get_channel_id_from_name(self, name):
        return self.channel_name_to_id.get(name)

    def get_channel_name_from_id(self, id):
        return self.channel_id_to_name.get(id)

    def get_user_id_from_name(self, name):
        return self.user_name_to_id.get(name)

    def get_user_name_from_id(self, id):
        return self.user_id_to_name.get(id)

    @tornado.gen.coroutine
    def reload_channels_cache(self):
        response = yield self.slack.api.channels.list(exclude_members=True)
        if response.code == 200 and response.data.ok:
            self.channel_name_to_id = { channel["name"]: channel["id"] for channel in response.data.channels }
            self.channel_id_to_name = { channel["id"]: channel["name"] for channel in response.data.channels }
            self.channel_is_in = { channel["id"] for channel in response.data.channels if channel["is_member"] }

    @tornado.gen.coroutine
    def reload_users_cache(self):
        response = yield self.slack.api.users.list(presence=False)
        if response.code == 200 and response.data.ok:
            self.user_name_to_id = { member["name"]: member["id"] for member in response.data.members }
            self.user_id_to_name = { member["id"]: member["name"] for member in response.data.members }

    @tornado.gen.coroutine
    def autofetch(self, delay=60):
        """Autofetch caches every {delay} minutes
        """
        self.autofetch_enabled = True
        interval = 1
        while self.autofetch_enabled:
            # this allows autofetch to be disabled at a 1 minute delay rather than 60 minutes
            if interval % delay == 0:
                yield self.fetch_all()
                interval = 1
            yield tornado.gen.sleep(60) # sleep 60 seconds

    @tornado.gen.coroutine
    def fetch_all(self):
        yield self.reload_users_cache()
        yield self.reload_channels_cache()

    def stop():
        self.autofetch_enabled = False

