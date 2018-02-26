import time
from .celery import app
from pprint import pprint
import yaml
import json
from .utils import Utils
import logging


logger = logging.getLogger(__name__)

u = Utils()


@app.task
def callback(full_data):
    full_data = json.loads(full_data)
    response = {'channel': full_data['channel']['id'],  # Should not be changed
                'as_user': True,  # Should not be changed
                'text': '',
                'attachments': [],
                'thread_reply': False,  # Only here for the response, does not get passed to the api call
                }
    try:
        for command_name in u.channel_to_actions[full_data['channel']['name']]:
            command = u.commands[command_name]
            parsed_response = command.p.parse(full_data['message']['text'], full_post=full_data)
            if parsed_response is not None:
                response.update(parsed_response)
                break
        if response.get('thread_reply') is True or full_data['message'].get('thread_ts') is not None:
            # Reply to the message using a thread
            response['thread_ts'] = full_data['message'].get('thread_ts', full_data['message']['ts'])
            try:
                del response['thread_reply']  # Cannot be passed to the api_call fn
            except KeyError:
                pass
        if response.get('reaction', '') != '':
            u.slack_client.api_call("reactions.add",
                                    channel=full_data['channel']['id'],
                                    name=response['reaction'],
                                    timestamp=full_data['message']['ts']
                                    )
            try:
                del response['reaction']  # Cannot be passed to the api_call fn
            except KeyError:
                pass
        if len(response.get('text', '').strip()) > 0 or len(response.get('attachments', [])) > 0:
            # Only post a message if needed. Reason not to would be the item got queued
            u.slack_client.api_call("chat.postMessage", **response)

    except Exception as e:
        logger.exception("Task failed: {data}".format(data=full_data))
        try:
            response['text'] = "The task has failed: `{e}`".format(e=e)
            u.slack_client.api_call("chat.postMessage", **response)
        except Exception:
            logger.exception("Failed trying to let the user know that the task failed")


