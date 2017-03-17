import re
import logging
from regex_decorator import Parser

logger = logging.getLogger(__name__)


class Example:

    def __init__(self, utils):
        self.utils = utils
        self.p = Parser()

        self.test = self.p.listener('test (.+)', re.IGNORECASE, parse_using='re')(self.test)
        self.queue = self.p.listener(self.utils.BOT_NAME + ' queue (.+)', re.IGNORECASE, parse_using='re')(self.queue)

    def test(self, matched_str, value, full_post={}):
        message_data = {'text': "Test value is: {value}".format(value=value),
                        'attachments': [],
                        }
        return message_data

    def queue(self, matched_str, value, full_post={}):
        message_data = {}

        if self.utils.is_worker is False:
            return {'text': "", 'add_to_queue': True}

        # Do the real work here and return with data
        message_data['text'] = "This value *{value}* came from a worker".format(value=value)
        message_data['thread_reply'] = True
        return message_data

    def help(self):
        text = """
- test [some_text]
- {bot_name} queue [some_text]
               """.format(bot_name=self.utils.BOT_NAME)
        message_data = {'attachments': [{'title': "Example Commands",
                                         'color': "#2f7a30",
                                         'text': text,
                                         'mrkdwn_in': ['text', 'pretext'],
                                         'thumb_url': "",
                                         }],
                        }
        return message_data
