import json
import time
import logging
from slackbot_queue import worker  # Needed for adding things to the queue

logger = logging.getLogger(__name__)


class Example:

    def __init__(self, slack):
        self.slack = slack
        self.parser = slack.Parser()

        self.long_task = self.parser.trigger('message', 'task (.+)')(self.long_task)
        self.reaction = self.parser.trigger('reaction_added', '(.*)', '.*')(self.reaction)

    def long_task(self, matched_str, value, full_event={}):
        """ Add a task to the queue and return a message letting the user know
        The worker will then post a message when it is completed
        """
        if full_event.get('is_worker', False) is False:
            worker.delay(json.dumps(full_event))
            return {'text': "Adding the task *{task}* to the queue".format(task=value)}

        # Some long running task...
        time.sleep(10)

        # @mention the user who added the task
        user = '<@{user_id}>'.format(user_id=full_event['user']['id'])
        message_data = {'text': "{user}: The task *{task}* is complete :tada:".format(user=user, task=value)}

        return message_data

    def reaction(self, reaction_str, message_str, reaction_value, full_event={}):
        """ Any time a user adds a reaction, the bot will add the thumbsup reaction to the same message/file
        """
        message_data = {'method': 'reactions.add',
                        'name': reaction_str,
                        }
        # Need to know what message or file to add the reaction to
        if full_event['reaction']['item']['type'] == 'message':
            message_data['timestamp'] = full_event['message']['ts']

        elif full_event['reaction']['item']['type'] == 'file':
            message_data['file'] = full_event['file']['id']

        return message_data

    def help(self):
        """ This is called when the user types `help` or `@botname help`
        """
        text = ('- task <task name>\n'
                '- Add a reaction, and the bot will react with the same thing\n'
                )
        message_data = {'attachments': [{'title': "Example Commands",
                                         'color': "#2f7a30",
                                         'text': text,
                                         'mrkdwn_in': ['text', 'pretext'],
                                         }],
                        }
        return message_data
