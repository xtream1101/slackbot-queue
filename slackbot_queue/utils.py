import os
import yaml
import urllib
import logging
import urllib.error
import urllib.request
from slackclient import SlackClient

logger = logging.getLogger(__name__)


class Utils:
    """
    Shared functions
    """

    def __init__(self):
        self.CONFIG = yaml.load(open(os.environ['SB_CONFIG'], 'r'))
        self._cmd_path = os.environ['SB_CMD']
        if os.environ.get('SB_WORKER', 'true').lower() == 'false':
            self.is_worker = False
        else:
            self.is_worker = True

        self.slack_client = SlackClient(self.CONFIG['SLACK_TOKEN'])
        self.channels = self._get_channel_list()
        self.groups = self._get_group_list()
        self.channels.update(self.groups)  # Need this for private channels

        self.users = self._get_user_list()
        self.ims = self._get_im_list()

        self.BOT_ID = self.users[self.CONFIG['BOT_NAME']]['id']
        self.BOT_NAME = '<@{}>'.format(self.BOT_ID)

        self.commands = self._load_commands()  # Needs to be after BOT_NAME is set

        self.channel_to_actions = self.CONFIG['CHANNEL_TO_ACTIONS']

    ###
    # Slack Functions
    ###
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

    def reload_im_list(self):
        self.ims = self._get_im_list()

    def reload_user_list(self):
        self.users = self._get_user_list()

    ###
    # System Functions
    ###
    def download(self, url, file_):
        """
        file_ is either a string (filename & path) to save the data to, or an in-memory object
        """
        rdata = None

        base_dir = 'tmp_downloads'

        try:
            request = urllib.request.Request(url)
            request.add_header('Authorization', 'Bearer {}'.format(self.CONFIG['SLACK_TOKEN']))
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
