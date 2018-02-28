import os
import re
import time
import logging
from pprint import pprint
from collections import defaultdict
from slackclient import SlackClient

logger = logging.getLogger(__name__)


class SlackController:

    def __init__(self):
        # Instantiate Slack client
        self.slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
        self.channels = self._get_channel_list()
        self.channels.update(self._get_group_list())
        self.users = self._get_user_list()
        self.ims = self._get_im_list()
        self.BOT_NAME = '<@{}>'.format(self.slack_client.api_call('auth.test')['user_id'])
        self.channel_to_actions = defaultdict(list)  # Filled in by the user

    def add_commands(self, channel_commands):
        for channel, commands in channel_commands.items():
            for command in commands:
                self.channel_to_actions[channel].append(command(self))

    def start_listener(self):
        # constants
        RTM_READ_DELAY = 1  # 1 second delay between reading from RTM

        if self.slack_client.rtm_connect(with_team_state=False):
            logger.info("Starter Bot connected and running!")

            while True:
                self.parse_event(self.slack_client.rtm_read())
                time.sleep(RTM_READ_DELAY)
        else:
            logger.error("Connection failed. Exception traceback printed above.")

    def parse_event(self, slack_events):
        """
            Parses a list of events coming from the Slack RTM API to find bot commands.
            If a bot command is found, this function returns a tuple of command and channel.
            If its not found, then this function returns None, None.
        """
        for event in slack_events:
            if event['type'] == 'message' and not 'subtype' in event:
                self.handle_message_event(event)
            elif event['type'] == 'reaction_added':
                # be able to do something based off of this
                pass
            else:
                # Can handle other things like reactions and such
                pass

    def handle_message_event(self, message_event):
        """
            Executes bot command if the command is known
        """
        # Get channel/DM data
        channel_data = None
        for _ in range(2):
            if message_event['channel'] in self.channels:
                channel_data = self.channels[message_event['channel']]

            elif message_event['channel'] in self.ims:
                channel_data = self.ims[message_event['channel']]
                channel_data['name'] = '__direct_message__'

            if channel_data is not None:
                break
            else:
                # Refresh both channels and ims and try again
                self.reload_channel_list()
                self.reload_im_list()

        try:
            user_data = self.users[message_event['user']]
        except KeyError:
            self.reload_user_list()
        finally:
            user_data = self.users[message_event['user']]

        full_data = {'channel': channel_data,
                     'message': message_event,
                     'user': user_data,
                     }

        if full_data['user'].get('is_bot') is False and (self.channel_to_actions.get(channel_data['name']) is not None or self.channel_to_actions.get('__all__') is not None):
            response = {'channel': channel_data['id'],  # Should not be changed
                        'as_user': True,  # Should not be changed
                        'text': '',
                        'attachments': [],
                        'thread_reply': False,  # Only here for the response, does not get passed to the api call
                        'add_to_queue': False,  # Only here for the response, does not get passed to the api call
                        }

            is_help_message = False
            help_messages_text = ['{bot_name} help'.format(bot_name=self.BOT_NAME),
                                  'help',
                                  ]
            if full_data['message']['text'] in help_messages_text:
                is_help_message = True

            all_commands = self.channel_to_actions.get(channel_data['name'], []) + self.channel_to_actions.get('__all__', [])
            for command in all_commands:
                if is_help_message is False:
                    parsed_response = command.p.parse(full_data['message']['text'])
                    if parsed_response is not None:
                        response.update(parsed_response)
                        break
                else:
                    try:
                        help_response = command.help().get('attachments')
                        if help_response is not None:
                            response['attachments'].extend(help_response)
                    except AttributeError as e:
                        logger.error("Missing help function in class: {e}".format(e=e))

            if len(response.get('text', '').strip()) > 0 or len(response.get('attachments', [])) > 0:
                # Only post a message if needed. Reason not to would be the item got queued
                self.slack_client.api_call('chat.postMessage', **response)

    def _get_channel_list(self):
            channels_call = self.slack_client.api_call("channels.list", exclude_archived=1)
            if channels_call['ok']:
                by_id = {item['id']: item for item in channels_call['channels']}
                by_name = {item['name']: item for item in channels_call['channels']}
                return {**by_id, **by_name}

    def _get_group_list(self):
        groups_call = self.slack_client.api_call("groups.list", exclude_archived=1)
        if groups_call['ok']:
            by_id = {item['id']: item for item in groups_call['groups']}
            by_name = {item['name']: item for item in groups_call['groups']}
            return {**by_id, **by_name}

    def _get_user_list(self):
        users_call = self.slack_client.api_call("users.list")
        if users_call['ok']:
            by_id = {item['id']: item for item in users_call['members']}
            by_name = {item['name']: item for item in users_call['members']}
            return {**by_id, **by_name}

    def _get_im_list(self):
        ims_call = self.slack_client.api_call("im.list")
        if ims_call['ok']:
            return {item['id']: item for item in ims_call['ims']}

    def reload_channel_list(self):
        self.channels = self._get_channel_list()
        self.channels.update(self._get_group_list())

    def reload_im_list(self):
        self.ims = self._get_im_list()

    def reload_user_list(self):
        self.users = self._get_user_list()




