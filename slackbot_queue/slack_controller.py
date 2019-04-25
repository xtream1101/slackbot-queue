import os
import re
import time
import json
import logging
import urllib.error
import urllib.request
from celery import Celery
from inspect import getargspec
from collections import defaultdict
from slackclient import SlackClient

logger = logging.getLogger(__name__)


class Parser:

    def __init__(self):
        self.message_listener = defaultdict(list)
        self.reaction_added_listener = defaultdict(list)
        self.file_share_listener = defaultdict(list)

    def trigger(self, *args, **kwargs):
        event_type = args[0]
        # Pass all other ars to the function (using [1:] to exclude the event_type)
        if event_type == 'message':
            return self._message(*args[1:], **kwargs)
        elif event_type == 'reaction_added':
            return self._reaction_added(*args[1:], **kwargs)
        elif event_type == 'file_share':
            return self._file_share(*args[1:], **kwargs)

    def _message(self, regex_str, flags=0):
        def wrapper(func):
            parse_with = re.compile(regex_str, flags)
            self.message_listener[func].append(parse_with)
            logger.info("Registered listener `{func_name}` to regex `{regex_str}`".format(func_name=func.__name__,
                                                                                          regex_str=regex_str))
            return func

        return wrapper

    def _reaction_added(self, reaction_regex, message_regex='.*', flags=0):
        def wrapper(func):
            reaction_parse = re.compile(reaction_regex, flags)
            message_parse = re.compile(message_regex, flags)
            self.reaction_added_listener[func].append({'reaction': reaction_parse,
                                                       'message': message_parse})
            logger.info("Registered listener `{func_name}` to regex `{reaction_regex}` & `{message_regex}`"
                        .format(func_name=func.__name__,
                                reaction_regex=reaction_regex,
                                message_regex=message_regex,
                                ))
            return func

        return wrapper

    def _file_share(self, filetype_regex, name_regex='.*', flags=0):
        def wrapper(func):
            filetype_parse = re.compile(filetype_regex, flags)
            name_parse = re.compile(name_regex, flags)
            self.file_share_listener[func].append({'filetype': filetype_parse,
                                                   'name': name_parse})
            logger.info("Registered listener `{func_name}` to regex `{filetype_regex}` & `{name_regex}`"
                        .format(func_name=func.__name__,
                                filetype_regex=filetype_regex,
                                name_regex=name_regex))
            return func

        return wrapper

    def parse_message(self, message_str, **kwargs):
        for callback in self.message_listener:
            for command in self.message_listener[callback]:
                result = re.search(command, message_str)
                if result is not None:
                    if len(result.groupdict().keys()) != 0:
                        rdata = callback(message_str, **result.groupdict(), **kwargs)
                    else:
                        cb_arg_spec = getargspec(callback)
                        # Ignore any named args
                        cb_arg_count = len(cb_arg_spec.args) - len(cb_arg_spec.defaults)
                        cb_arg_count -= 1  # Since the message_str is always passed
                        if cb_arg_spec.args[0] in ('self', 'cls'):
                            # Ignore self or cls args
                            cb_arg_count -= 1

                        if len(result.groups()) == cb_arg_count:
                            rdata = callback(message_str, *result.groups(), **kwargs)
                        else:
                            rdata = {}
                            if len(result.groups()) > cb_arg_count:
                                msg_amount = 'many'
                            else:
                                msg_amount = 'few'
                            logger.error("To {msg_amount} regex groups found for function {fn}"
                                         .format(msg_amount=msg_amount,
                                                 fn=callback.__name__))


                    return rdata

    def parse_reaction(self, reaction_str, message_str, **kwargs):
        for callback in self.reaction_added_listener:
            for command in self.reaction_added_listener[callback]:
                reaction_result = re.search(command['reaction'], reaction_str)
                message_result = re.search(command['message'], message_str)
                if reaction_result is not None and message_result is not None:
                    # BUG: Both regexes need to use named groups or normal groups, cannot be mixed
                    if len(reaction_result.groupdict().keys()) != 0:
                        rdata = callback(reaction_str, message_str,
                                         **reaction_result.groupdict(), **message_result.groupdict(), **kwargs)
                    else:
                        rdata = callback(reaction_str, message_str,
                                         *reaction_result.groups(), *message_result.groups(), **kwargs)
                    return rdata

    def parse_file_share(self, filetype_str, name_str, **kwargs):
        for callback in self.file_share_listener:
            for command in self.file_share_listener[callback]:
                filetype_result = re.search(command['filetype'], filetype_str)
                name_result = re.search(command['name'], name_str)
                if filetype_result is not None and name_result is not None:
                    # BUG: Both regexes need to use named groups or normal groups, cannot be mixed
                    if len(filetype_result.groupdict().keys()) != 0:
                        rdata = callback(filetype_str, name_str,
                                         **filetype_result.groupdict(), **name_result.groupdict(), **kwargs)
                    else:
                        rdata = callback(filetype_str, name_str,
                                         *filetype_result.groups(), *name_result.groups(), **kwargs)
                    return rdata


class SlackController:

    def __init__(self):
        self.Parser = Parser
        self.channel_to_actions = defaultdict(list)  # Filled in by the user

        # Defaults for the help message
        self.help_message_regex = None  # The user can override this, or it will default to whats in the setup()

    def add_commands(self, channel_commands):
        for channel, commands in channel_commands.items():
            for command in commands:
                self.channel_to_actions[channel].append(command)

    def setup(self, slack_bot_token=None):
        # Do not have this in __init__ because this is not needed when running tests
        self.SLACK_BOT_TOKEN = slack_bot_token
        if self.SLACK_BOT_TOKEN is None:
            self.SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')

        if self.SLACK_BOT_TOKEN is None:
            raise ValueError("Missing SLACK_BOT_TOKEN")

        self.slack_client = SlackClient(self.SLACK_BOT_TOKEN)
        self.channels = self._get_channel_list()
        self.channels.update(self._get_group_list())
        self.users = self._get_user_list()
        self.ims = self._get_im_list()
        self.BOT_ID = self.slack_client.api_call('auth.test')['user_id']
        self.BOT_NAME = '<@{}>'.format(self.BOT_ID)

        if self.help_message_regex is None:
            self.help_message_regex = re.compile('^(?:{bot_name} )?help$'.format(bot_name=self.BOT_NAME),
                                                 flags=re.IGNORECASE)

    def help(self, commands, slack_client, full_event={}):
        """Default help response

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

        for command in commands:
            try:
                parsed_response = command.help()
                if parsed_response is not None:
                    # Add the help message from the command to the return message
                    message_data['attachments'].extend(parsed_response.get('attachments', []))
            except AttributeError as e:
                logger.warning("Missing help function in class: {e}".format(e=e))

        return message_data

    def start_worker(self, argv=[]):
        queue.start(argv=argv)

    def start_listener(self):
        RTM_READ_DELAY = 1  # noqa, 1 second delay between reading from RTM

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
            logger.debug("Event:\n{event}".format(event=event))
            try:
                if (event['type'] == 'message' and
                        event.get('subtype', None) not in ['message_changed', 'message_deleted',
                                                           'file_share', 'message_replied']):
                    self.handle_message_event(event)
                elif event['type'] in ['reaction_added']:
                    self.handle_reaction_event(event)
                elif event.get('subtype') == 'file_share':
                    self.handle_file_share_event(event)
                else:
                    # Can handle other things like reactions and such
                    pass
            except Exception:
                logger.exception("Failed to parse event: {event}".format(event=event))

    def _get_all_channel_commands(self, full_data):
        # Get all commands in channel
        all_channel_commands = self.channel_to_actions.get(full_data['channel']['name'], [])
        # All commands that are in ALL channels. Make the list unique.
        # If not, if a command is in __all__ and another channel it will display the help twice
        #   (also loop through twice when checking commands)
        for command in self.channel_to_actions.get('__all__', []):
            if command not in all_channel_commands:
                all_channel_commands.append(command)

        return all_channel_commands

    def handle_reaction_event(self, reaction_event):
        if 'type' in reaction_event:
            # It came from slack
            # Get the mesage that the reaction was added to
            full_data = {'reaction': reaction_event,
                         'user': self._get_user_data(reaction_event['user']),
                         }

            if reaction_event['item']['type'] == 'message':
                full_data['message'] = self.slack_client.api_call(**{'method': 'conversations.history',
                                                                     'channel': reaction_event['item']['channel'],
                                                                     'limit': 1,
                                                                     'inclusive': True,
                                                                     'latest': reaction_event['item']['ts'],
                                                                     'oldest': reaction_event['item']['ts'],
                                                                     })['messages'][0]

            elif reaction_event['item']['type'] == 'file':
                try:
                    full_data['file'] = self.slack_client.api_call(**{'method': 'files.info',
                                                                      'file': reaction_event['item']['file'],
                                                                      })['file']
                except KeyError:
                    file_response = self.slack_client.api_call(**{'method': 'files.info',
                                                                  'file': reaction_event['item']['file'],
                                                                  })
                    if file_response['error'] != 'file_not_found':
                        logger.warning(file_response)

                    return  # No need to continue if we do not have access to the file

            # Add channel data
            for _ in range(1):
                try:
                    # If its a reaction on a message
                    channel_id = full_data['reaction']['item']['channel']
                except Exception: pass  # noqa: E701
                else: break  # It worked  # noqa: E701

                try:
                    # If its a reaction on an uploaded file to a dm/private channel
                    channel_id = full_data['file']['ims'][0]
                except Exception: pass  # noqa: E701
                else: break  # It worked  # noqa: E701

                try:
                    # If its a reaction on an uploaded file to a public channel
                    channel_id = full_data['file']['channels'][0]
                except Exception: pass  # noqa: E701
                else: break  # It worked  # noqa: E701

            full_data['channel'] = self._get_channel_data(channel_id)

        else:
            # It came from the worker queue, meaning the message_event already has the full data
            full_data = reaction_event

        # Do not ever trigger its self
        # Only parse the message if the message came from a channel that has commands in it
        if full_data['user']['id'] != self.BOT_ID and (self.channel_to_actions.get('__all__') or
                                                       self.channel_to_actions.get(full_data['channel']['name'])):
            response = {'channel': full_data['channel']['id'],
                        'as_user': True,  # Should not be changed
                        'method': 'chat.postMessage',
                        }

            # Get all commands in channel
            all_channel_commands = self._get_all_channel_commands(full_data)

            parsed_response = None
            for command in all_channel_commands:
                message_text = ' uploaded a file '
                if full_data.get('message') is not None:
                    message_text = full_data['message']['text']

                parsed_response = command.parser.parse_reaction(full_data['reaction']['reaction'],
                                                                message_text,
                                                                full_event=full_data)
                if parsed_response is not None:
                    response.update(parsed_response)
                    break

            if parsed_response is not None:
                # Only post a message if needed
                self.slack_client.api_call(**response)

    def handle_message_event(self, message_event):
        if 'type' in message_event:
            # It came from slack
            channel_data = self._get_channel_data(message_event['channel'])
            user_data = self._get_user_data(message_event['user'])

            full_data = {'channel': channel_data,
                         'message': message_event,
                         'user': user_data,
                         }
        else:
            # It came from the worker queue, meaning the message_event already has the full data
            full_data = message_event

        # Do not ever trigger its self
        # Only parse the message if the message came from a channel that has commands in it
        if full_data['user']['id'] != self.BOT_ID and (self.channel_to_actions.get('__all__') is not None or
                                                       self.channel_to_actions.get(full_data['channel']['name']) is not None):  # noqa: E501
            response = {'channel': full_data['channel']['id'],  # Should not be changed
                        'as_user': True,  # Should not be changed
                        'method': 'chat.postMessage',
                        }
            if full_data['message'].get('thread_ts') is not None:
                # This is so a message reply that is from a thread will auto stay in the thread
                response['thread_ts'] = full_data['message'].get('thread_ts')

            # Get all commands in channel
            all_channel_commands = self._get_all_channel_commands(full_data)

            parsed_response = None
            if re.match(self.help_message_regex, full_data['message']['text']) is None:
                # Not the help command, check other functions
                for command in all_channel_commands:
                    parsed_response = command.parser.parse_message(full_data['message']['text'],
                                                                   full_event=full_data)
                    if parsed_response is not None:
                        response.update(parsed_response)
                        break
            else:
                # The help command was triggered
                parsed_response = self.help(all_channel_commands, self.slack_client, full_event=full_data)
                if parsed_response is not None:
                    response.update(parsed_response)

            if parsed_response is not None:
                # Only post a message if needed
                response = self.slack_client.api_call(**response)
                logger.debug("Slack api response: {response}".format(response=response))

    def handle_file_share_event(self, file_share_event):
        if 'type' in file_share_event:
            # It came from slack
            channel_data = self._get_channel_data(file_share_event['channel'])
            user_data = self._get_user_data(file_share_event['user'])

            full_data = {'channel': channel_data,
                         'file_share': file_share_event,
                         'user': user_data,
                         }
        else:
            # It came from the worker queue, meaning the file_share_event already has the full data
            full_data = file_share_event

        # Do not ever trigger its self
        # Only parse the message if the message came from a channel that has commands in it
        if full_data['user']['id'] != self.BOT_ID and (self.channel_to_actions.get('__all__') is not None or
                                                       self.channel_to_actions.get(full_data['channel']['name']) is not None):  # noqa: E501
            response = {'channel': full_data['channel']['id'],  # Should not be changed
                        'as_user': True,  # Should not be changed
                        'method': 'chat.postMessage',
                        'attachments': [],  # Needed for the help command
                        }
            if full_data['file_share'].get('thread_ts') is not None:
                response['thread_ts'] = full_data['file_share'].get('thread_ts')

            # Get all commands in channel
            all_channel_commands = self._get_all_channel_commands(full_data)

            parsed_response = None
            for command in all_channel_commands:
                parsed_response = command.parser.parse_file_share(full_data['file_share']['file']['filetype'],
                                                                  full_data['file_share']['file']['name'],
                                                                  full_event=full_data)
                if parsed_response is not None:
                    response.update(parsed_response)
                    break

            if parsed_response is not None:
                # Only post a message if needed
                response = self.slack_client.api_call(**response)
                logger.debug("Slack api response: {response}".format(response=response))

    def _get_channel_data(self, channel):
        channel_data = None
        for _ in range(2):
            if channel in self.channels:
                channel_data = self.channels[channel]

            elif channel in self.ims:
                channel_data = self.ims[channel]
                channel_data['name'] = '__direct_message__'

            if channel_data is not None:
                break
            else:
                # Refresh both channels and ims and try again
                self.reload_channel_list()
                self.reload_im_list()

        return channel_data

    def _get_user_data(self, user):
        try:
            user_data = self.users[user]
        except KeyError:
            self.reload_user_list()
        finally:
            user_data = self.users[user]

        return user_data

    def _get_channel_list(self):
        channels_call = self.slack_client.api_call("channels.list", exclude_archived=1)
        logger.debug("_get_channel_list: " + str(channels_call))
        if channels_call['ok']:
            by_id = {item['id']: item for item in channels_call['channels']}
            by_name = {item['name']: item for item in channels_call['channels']}
            return {**by_id, **by_name}

    def _get_group_list(self):
        groups_call = self.slack_client.api_call("groups.list", exclude_archived=1)
        logger.debug("_get_group_list: " + str(groups_call))
        if groups_call['ok']:
            by_id = {item['id']: item for item in groups_call['groups']}
            by_name = {item['name']: item for item in groups_call['groups']}
            return {**by_id, **by_name}

    def _get_user_list(self):
        users_call = self.slack_client.api_call("users.list")
        logger.debug("_get_user_list: " + str(users_call))
        if users_call['ok']:
            by_id = {item['id']: item for item in users_call['members']}
            by_name = {item['name']: item for item in users_call['members']}
            return {**by_id, **by_name}

    def _get_im_list(self):
        ims_call = self.slack_client.api_call("im.list")
        logger.debug("_get_im_list: " + str(ims_call))
        if ims_call['ok']:
            return {item['id']: item for item in ims_call['ims']}

    def reload_channel_list(self):
        self.channels = self._get_channel_list()
        self.channels.update(self._get_group_list())

    def reload_im_list(self):
        self.ims = self._get_im_list()

    def reload_user_list(self):
        self.users = self._get_user_list()

    def download(self, url, file_):
        """
        file_ is either a string (filename & path) to save the data to, or an in-memory object
        """
        rdata = None
        base_dir = 'tmp_downloads'

        try:
            request = urllib.request.Request(url)
            request.add_header('Authorization', 'Bearer {}'.format(self.SLACK_BOT_TOKEN))
            # urllib downloads files a bit faster then requests does
            with urllib.request.urlopen(request) as response:
                data = response.read()
                if isinstance(file_, str):
                    file_path = os.path.abspath(os.path.join(base_dir, file_))

                    try: os.mkdir(os.path.dirname(file_path))  # noqa
                    except FileExistsError: pass  # noqa

                    with open(file_path, 'wb') as out_file:
                        out_file.write(data)

                    rdata = file_path

                else:
                    file_.write(data)
                    file_.seek(0)

                    rdata = file_

        except urllib.error.HTTPError as e:
            logger.error("Download Http Error `{}` on {}".format(e.code, url))

        except Exception:
            logger.exception("Download Error on {}".format(url))

        return rdata


slack_controller = SlackController()
queue = Celery()


@queue.task
def worker(full_event):
    full_event = json.loads(full_event)
    full_event['is_worker'] = True
    if 'reaction' in full_event:
        slack_controller.handle_reaction_event(full_event)
    elif 'file_share' in full_event:
        slack_controller.handle_file_share_event(full_event)
    else:
        slack_controller.handle_message_event(full_event)
