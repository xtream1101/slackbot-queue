import re  # noqa
import logging
import argparse
from slackbot_queue import slack_controller, queue
# import commands here
from example import Example
from example2 import Example2

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='Slackbot with task queue')
parser.add_argument('-w', '--worker', action='store_true', help='If set, this will run as a worker')
args = parser.parse_args()


def custom_help(commands, full_event, slack_client):
    """ This is currently what the default function does.

        Args:
            commands (list): List of the command classes that are in the channel where help was triggered
            full_event (dict): All of the data from the slack client
            slack_client (SlackClient): Api to send message directly to the slack api

        Returns:
            dict/None: dict of dat to send to the slack api
                       the keys `channel` & `as_user` & `method` are added before posting on return

    """
    message_data = {'method': 'chat.postEphemeral',
                    'user': full_event['user']['id'],
                    'text': 'Here are all the commands available in this channel',
                    'attachments': [],
                    }

    # # Add a reaction the the help command so others know the bot responded (not in the default help function)
    # slack_client.api_call(**{'method': 'reactions.add',
    #                          'name': 'ok_hand',
    #                          'channel': full_event['channel']['id'],
    #                          'timestamp': full_event['message']['ts'],
    #                          })

    for command in commands:
        try:
            parsed_response = command.help()
            if parsed_response is not None:
                # Add the help message from the command to the return message
                message_data['attachments'].extend(parsed_response.get('attachments', []))
        except AttributeError as e:
            logger.warning("Missing help function in class: {e}".format(e=e))

    return message_data


queue.conf.task_default_queue = 'custom_slackbot'
queue.conf.broker_url = 'amqp://guest:guest@localhost:5672//'

# By default the slack token is set by the env var `SLACK_BOT_TOKEN`
# But can also be passed in as a named arg to setup as `slack_bot_token="token_here"` and will override the env var
slack_controller.setup()

# # Set a custom regex for the help message trigger. This is the current defult if not manually set
# # Needs to be after .setup() if using the bot_name/id
# slack_controller.help_message_regex = re.compile('^(?:{bot_name} )?help$'.format(bot_name=slack_controller.BOT_NAME),
#                                                  flags=re.IGNORECASE)

# # Set a custom help function action.
# slack_controller.help = custom_help

# Each class needs to be passed the `slack_controller`
example = Example(slack_controller)
example2 = Example2(slack_controller)

# Order of the commands in the channel matter, the first match it finds it will stop
# The order of the channels do not matter though
commands = {'__direct_message__': [],
            '__all__': [example, example2],
            'bot-dev-1': [],
            'general': [],
            }
slack_controller.add_commands(commands)


if __name__ == '__main__':
    if args.worker is False:
        slack_controller.start_listener()
    else:
        slack_controller.start_worker(argv=['celery', 'worker', '--concurrency', '1', '-l', 'info'])
