# Slackbot Queue

Slackbot with a celery queue for long running tasks

This can be run even without a celery queue as long as you do not try and add things to the worker. Just run the listener and all the features (besides having a worker queue) will still work.


### Install
`pip install slackbot-queue`  


### Usage
The `example` folder has a lot more to show and is ready to run

```python
from slackbot_queue import slack_controller, queue

from example import Example  # Import the example command class

# Set up the celery configs
queue.conf.task_default_queue = 'custom_slackbot'
queue.conf.broker_url = 'amqp://guest:guest@localhost:5672//'

# The token could also be set by the env variable SLACK_BOT_TOKEN
slack_controller.setup(slack_bot_token='xxxxxxxx')

# Set up the command by passing in the slack_controller to it
ex = Example(slack_controller)

# Set up the example command to only work in the `general` channel or as a direct message
slack_controller.add_commands({'__direct_message__': [ex],
                               '__all__': [],
                               'general': [ex],
                               })

# Either start the listener
slack_controller.start_listener()

# Or the worker:
# The argv list is celery arguments used to start the worker
slack_controller.start_worker(argv=['celery', 'worker', '--concurrency', '1', '-l', 'info'])
```

A full example can be found in the `example` dir.

Slacks api docs: https://api.slack.com/methods

If the command function returns `None`, that means that the bot will continue to check the rest of the commands.  
But if the command does return something, no other commands will be checked. Meaning that if there are 2 commands that are looking for the same message regex, the command listed first in the channel list will be the only one triggered.

If you want multiple commands to get triggered by the same message, you can have them return `None`, but sill post to slack inside you function by doing `self.slack.slack_client.api_call(**message_data)`.  
`message_data` is the same as you would normally return but with the added keys (which are normally added when the data gets returned):  
```
'method': 'chat.postMessage',  # or any other method slack supports
'channel': full_event['channel']['id'],
'as_user': True,
```
