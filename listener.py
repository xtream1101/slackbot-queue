import time
import json
import logging
from utils import Utils
from pprint import pprint

logger = logging.getLogger(__name__)


class Listener(Utils):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
        if self.slack_client.rtm_connect():
            logger.info("StarterBot connected and running!")
            while True:
                message_data = self.parse_slack_output(self.slack_client.rtm_read())
                if message_data is not None:
                    self.handle_command(message_data)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            logger.critical("Connection failed. Invalid Slack token or bot ID?")

    def parse_slack_output(self, slack_rtm_output):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output:
                    return output
        return None

    def handle_command(self, message_data):
        """
            Receives commands directed at the bot and determines if they
            are valid commands. If so, then acts on the commands. If not,
            returns back what it needs for clarification.
        """
        # pprint(message_data)
        # Get channel/DM data
        channel_data = None
        for _ in range(2):
            if message_data['channel'] in self.channels:
                channel_data = self.channels[message_data['channel']]

            elif message_data['channel'] in self.ims:
                channel_data = self.ims[message_data['channel']]
                channel_data['name'] = '__direct_message__'

            if channel_data is not None:
                break
            else:
                # Refresh both channels and ims and try again
                self.reload_channel_list()
                self.reload_im_list()

        try:
            user_data = self.users[message_data['user']]
        except KeyError:
            self.reload_user_list()
        finally:
            user_data = self.users[message_data['user']]

        full_data = {'channel': channel_data,
                     'message': message_data,
                     'user': user_data,
                     }

        # pprint(full_data)

        if full_data['user'].get('is_bot') is False and self.channel_to_actions.get(channel_data['name']) is not None:
            response = {'channel': channel_data['id'],  # Should not be changed
                        'as_user': True,  # Should not be changed
                        'text': '',
                        'attachments': [],
                        'thread_reply': False,  # Only here for the response, does not get passed to the api call
                        'add_to_queue': False,  # Only here for the response, does not get passed to the api call
                        }

            is_help_message = False
            help_message_text = '{bot_name} help'.format(bot_name=self.BOT_NAME)
            if full_data['message']['text'] == help_message_text:
                is_help_message = True

            for command_name in self.channel_to_actions[channel_data['name']]:
                command = self.commands[command_name]

                if is_help_message is False:
                    parsed_response = command.p.parse(full_data['message']['text'], full_post=full_data)
                    if parsed_response is not None:
                        response.update(parsed_response)
                        break
                else:
                    # Get all help messages
                    help_response = command.help().get('attachments')
                    if help_response is not None:
                        response['attachments'].extend(help_response)

            if response.get('thread_reply') is True or message_data.get('thread_ts') is not None or is_help_message is True:
                # Reply to the message using a thread
                response['thread_ts'] = message_data.get('thread_ts', message_data['ts'])
                try:
                    del response['thread_reply']  # Cannot be passed to the api_call fn
                except KeyError:
                    pass

            if response.get('add_to_queue') is True:
                for i in range(2):
                    try:
                        self.mq.basic_publish(exchange='',
                                              routing_key=self.mq_name,
                                              body=json.dumps(full_data))

                    except:
                        # From utils, re create the connection
                        self._setup_rabbitmq()
                        if i == 1:
                            logger.exception("Failed to reconnect to rabbitmq")

            try:
                del response['add_to_queue']  # Cannot be passed to the api_call fn
            except KeyError:
                pass

            if len(response.get('text', '').strip()) > 0 or len(response.get('attachments', [])) > 0:
                # Only post a message if needed. Reason not to would be the item got queued
                self.slack_client.api_call("chat.postMessage", **response)
