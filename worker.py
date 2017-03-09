import json
import logging
from utils import Utils

logger = logging.getLogger(__name__)


class Worker(Utils):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mq.basic_qos(prefetch_count=1)
        self.mq.basic_consume(self.callback, queue=self.CONFIG['RABBITMQ']['QUEUE_NAME'])
        self.mq.start_consuming()

    def callback(self, ch, method, properties, full_data):
        full_data = json.loads(full_data.decode('utf-8'))
        response = {'channel': full_data['channel_data']['id'],  # Should not be changed
                    'as_user': True,  # Should not be changed
                    'text': '',
                    'attachments': [],
                    'thread_reply': False,  # Only here for the response, does not get passed to the api call
                    }

        for command_name in self.channel_to_actions[full_data['channel_data']['name']]:
            command = self.commands[command_name]

            parsed_response = command.p.parse(full_data['message_data']['text'])
            if parsed_response is not None:
                response.update(parsed_response)
                break

        if response.get('thread_reply') is True or full_data['message_data'].get('thread_ts') is not None:
            # Reply to the message using a thread
            response['thread_ts'] = full_data['message_data'].get('thread_ts', full_data['message_data']['ts'])
            try:
                del response['thread_reply']  # Cannot be passed to the api_call fn
            except KeyError:
                pass

        if len(response.get('text', '').strip()) > 0 or len(response.get('attachments', [])) > 0:
            # Only post a message if needed. Reason not to would be the item got queued
            self.slack_client.api_call("chat.postMessage", **response)

        # Remove the messge from the queue
        ch.basic_ack(delivery_tag=method.delivery_tag)
