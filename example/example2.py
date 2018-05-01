import re
import logging
from pprint import pprint  # noqa

logger = logging.getLogger(__name__)


class Example2:

    def __init__(self, slack):
        # Slack client docs: https://github.com/slackapi/python-slackclient
        # All Slack methods: https://api.slack.com/methods/
        # Gives you access to `self.slack.slack_client` to be able to do even more custom stuff like in `multi_action()`
        self.slack = slack

        # The order that these triggers are setup in matters.
        # It will run the function of the first one it matches with
        self.parser = slack.Parser()

        # Listen for the @bot-name in the message
        self.add_reaction = self.parser.trigger('message', 'Hi {bot}'.format(bot=self.slack.BOT_NAME)
                                                )(self.add_reaction)

        # Make the string match case incentive
        # `flags` is the same flags that get passed to `re`:
        #       https://docs.python.org/3/library/re.html#contents-of-module-re
        self.comment_reply = self.parser.trigger('message', 'thread me', flags=re.IGNORECASE)(self.comment_reply)

        # Multiple reactions and a message
        self.multi_action = self.parser.trigger('message', '^multi action$', flags=re.IGNORECASE)(self.multi_action)

        # Reply to a csv upload
        self.file_reply = self.parser.trigger('file_share', 'csv')(self.file_reply)

        # Listen for the reaction: "grin"
        #          on the message: "react"
        self.reaction_action = self.parser.trigger('reaction_added', 'grin', '^react$',
                                                   flags=re.IGNORECASE)(self.reaction_action)

    def add_reaction(self, matched_str, full_event={}):
        """ Add reaction to a message
        """
        message_data = {'method': 'reactions.add',
                        'name': 'wave',
                        'timestamp': full_event['message']['ts'],
                        }
        return message_data

    def comment_reply(self, matched_str, full_event={}):
        """ Add a reply to the message
        """
        if full_event['message'].get('thread_ts') is not None:
            # The message is already in a thread, add the reply to the correct message
            message_data = {'text': 'This is a thread reply',
                            'thread_ts': full_event['message'].get('thread_ts'),
                            }
        else:
            # Create a new thread for this message
            message_data = {'text': 'This is a thread reply',
                            'thread_ts': full_event['message']['ts'],
                            }

        return message_data

    def multi_action(self, matched_str, full_event={}):
        """ Add multiple reactions and post a message
        """

        # Add the first reaction
        message_data = {'method': 'reactions.add',
                        'name': 'wave',
                        'channel': full_event['channel']['id'],
                        'timestamp': full_event['message']['ts'],
                        }
        self.slack.slack_client.api_call(**message_data)

        # Add another reaction (could be anything though)
        message_data = {'method': 'reactions.add',
                        'name': '+1',
                        'channel': full_event['channel']['id'],
                        'timestamp': full_event['message']['ts'],
                        }
        self.slack.slack_client.api_call(**message_data)

        # And reply with a message, otherwise return `{}` if you do not want any other function to get triggered
        return {'text': "Yeah, thats right. I just did that."}

    def file_reply(self, type_str, name_str, full_event={}):
        """ Add a comment to a file
        """
        message_data = {'method': 'files.comments.add',
                        'file': full_event['file_share']['file']['id'],
                        'comment': 'This is a file comment',
                        }

        # This will reply to a file as a threaded message (which is not a thing you can normally do)
        # message_data = {'thread_ts': full_event['file_share']['event_ts'],
        #                 'comment': 'This is a reply to a file',
        #                 }

        return message_data

    def reaction_action(self, reaction_str, message_str, full_event={}):
        """ Listen for a reaction and post a message in response
        """
        # # Only listen for reactions on the message posted by the bot
        # if full_event['message']['user'] != self.slack.BOT_ID:
        #     # Make sure the user was this bot
        #     return None

        message_data = {'text': ":+1:"}
        return message_data

    def help(self):
        """ This is called when the user types `help` or `@botname help`
        """
        text = ('- Hi {bot}'
                '\n- thread me'
                '\n- react'
                '\n- multi action'
                '\n- upload a csv file'
                '\n- Add a :grin: reaction to a message that is just "reply"'
                '\n').format(bot=self.slack.BOT_NAME)
        message_data = {'attachments': [{'title': "Example2 Commands",
                                         'color': "#2BB8DE",
                                         'text': text,
                                         'mrkdwn_in': ['text', 'pretext'],
                                         }],
                        }
        return message_data
