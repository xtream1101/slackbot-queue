import logging

logger = logging.getLogger(__name__)


class Example2:

    def __init__(self, slack):
        self.slack = slack
        self.parser = slack.Parser()

        self.foo = self.parser.trigger('message', 'example2')(self.foo)

    def foo(self, matched_str, full_event={}):
        """ Respond to the text `example2`
        """
        message_data = {'text': "This is from example 2"}
        return message_data

    def help(self):
        """ This is called when the user types `help` or `@botname help`
        """
        message_data = {'attachments': [{'title': "Example2 Commands",
                                         'color': "#FF0000",
                                         'text': 'Responds to the text `example2`',
                                         'mrkdwn_in': ['text', 'pretext'],
                                         }],
                        }
        return message_data
