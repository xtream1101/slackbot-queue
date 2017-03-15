import os
import pika
import urllib
import logging
import importlib.machinery
from slackclient import SlackClient

logger = logging.getLogger(__name__)


class Utils:
    """
    Shared functions
    """

    def __init__(self, config, cmd_path, is_worker=False):
        self.CONFIG = config
        self._cmd_path = cmd_path
        self.is_worker = is_worker

        self.slack_client = SlackClient(self.CONFIG['SLACK_TOKEN'])
        self.channels = self._get_channel_list()
        self.users = self._get_user_list()
        self.ims = self._get_im_list()

        self.BOT_ID = self.users[self.CONFIG['BOT_NAME']]['id']
        self.BOT_NAME = '<@{}>'.format(self.BOT_ID)

        self.commands = self._load_commands()  # Needs to be after BOT_NAME is set

        self.channel_to_actions = self.CONFIG['CHANNEL_TO_ACTIONS']

        self.mq_name = self.CONFIG['RABBITMQ']['QUEUE_NAME']
        self.mq = self._setup_rabbitmq()  # Needs to be after mq_name is set

    ###
    # Slack Functions
    ###
    def _get_channel_list(self):
        channels_call = self.slack_client.api_call("channels.list", exclude_archived=1)
        if channels_call['ok']:
            by_id = {item['id']: item for item in channels_call['channels']}
            by_name = {item['name']: item for item in channels_call['channels']}
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
    # Rabbitmq Functions
    ###
    def _setup_rabbitmq(self):
        credentials = pika.PlainCredentials(self.CONFIG['RABBITMQ'].get('USER', 'guest'),
                                            self.CONFIG['RABBITMQ'].get('PASSWORD', 'guest'))
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.CONFIG['RABBITMQ']['HOST'],
                                                                       credentials=credentials,
                                                                       virtual_host=self.CONFIG['RABBITMQ'].get('VHOST', '/')))
        mq = connection.channel()
        mq.queue_declare(queue=self.mq_name, durable=True)

        return mq

    ###
    # System Functions
    ###
    def _load_commands(self):
        rdata = {}
        command_files = os.listdir(self._cmd_path)
        for file in command_files:
            if not file.startswith('__') and file.endswith('.py'):
                file_name = file.replace('.py', '')
                class_name = file_name.replace('_', ' ').title().replace(' ', '')

                file_path = os.path.join(self._cmd_path, file)
                loader = importlib.machinery.SourceFileLoader(file_name, file_path).load_module()
                cls_name = getattr(loader, class_name)

                rdata[file_name] = cls_name(utils=self)

        return rdata

    def download(self, url, filename):
        """
        :return: absolute path of file
        """
        rdata = None

        base_dir = 'tmp_downloads'
        try:
            os.mkdir(base_dir)
        except FileExistsError:
            pass

        file_path = os.path.join(base_dir, filename)

        try:
            request = urllib.request.Request(url)
            request.add_header('Authorization', 'Bearer {}'.format(self.CONFIG['SLACK_TOKEN']))
            # urllib downloads files a bit faster then requests does
            with urllib.request.urlopen(request) as response, open(file_path, 'wb') as out_file:
                data = response.read()
                out_file.write(data)

        except urllib.error.HTTPError as e:
            rdata = None
            # We do not need to show the user 404 errors
            if e.code != 404:
                logger.exception("Download Http Error ({})".format(url))

        except Exception:
            rdata = None
            logger.exception("Download Error: ".format(url))

        finally:
            rdata = os.path.abspath(file_path)

        return rdata
