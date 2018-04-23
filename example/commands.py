import os
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

queue.conf.task_default_queue = 'custom_slackbot'
queue.conf.broker_url = 'amqp://guest:guest@localhost:5672//'

# By default the slack token is set by the env var `SLACK_BOT_TOKEN`
# But can also be passed in as a named arg to setup as `slack_bot_token="token_here"`
slack_controller.setup()

# Each class needs to be passed the `slack_controller`
example = Example(slack_controller)
example2 = Example2(slack_controller)

# Order of the commands in the channel matter, the first match it finds it will stop
# The order of the channels do not matter though
commands = {'__direct_message__': [],
            '__all__': [example, example2],
            'general': [],
            }
slack_controller.add_commands(commands)


if __name__ == '__main__':
    if args.worker is False:
        slack_controller.start_listener()
    else:
        slack_controller.start_worker(argv=['celery', 'worker', '--concurrency', '1', '-l', 'info'])
