
import re
import uuid
import logging

class Extension(object):

    def __init__(self):
        self.listeners = {}

    def add_listener(self, func, name=None):
        name = name or uuid.uuid4()
        self.listeners[name] = func

    def remove_listener(self, name):
        return self.listeners.pop(name, None)

    def fire(self, *args, **kwargs):
        for listener_name, listener in self.listeners.items():
            try:
                listener(*args, **kwargs)
            except Exception as e:
                import traceback; traceback.print_exc()


class OnMentionExtension(Extension):

    def __init__(self, slackbot, user_id):
        super().__init__()
        self.regex = re.compile("(?P<user>\<@{user}\>)".format(user=user_id))
        self.user_id = user_id

    def __call__(self, event):
        try:
            text = event.get("text")
            if text is None:
                return
            found = self.regex.search(text)
            if not found:
                return

            self.fire(user_id=event["user"], channel_id=event["channel"],
                    mention_user_id=self.user_id, event=event,
                    start_index=found.start(), end_index=found.end())
        except Exception as e:
            import traceback; traceback.print_exc()

