# Slack Task Queue

Version: 0.1.4

This project enables large tasks to be run on distributed workers so it will not lock up or crash the main bot. Not all commands have to use the workers but the tasks that are known to need more cpu/ram/etc then what the bot is running on would use the workers.

This repo contains the core of the slackbot. The commands to listen for and the actions to take can be stored in its own repo. There is a folder `example` which has example commands and a default config file to demo how to use project.

### Args
- `-c` or `--command-path`: This is required and is the folder path that contains the `config.yaml` and the other python files that have the commands/tasks in them
- `-w` or `--worker`: Set this flag to denote that this instance is a worker
- `-f` or `--config-file`: Use this flag if the config file is called something other than `config.yaml`


### Usage
Must use python 3.5.x or later.
Must have a RabbitMQ server running somewhere where this bot can access (set in the config file)
`$ pip3 install -r requirements.txt`
`$ python3 main.py -c ./example [-w]`
There must be **only** one non-worker _(listener)_ and at least one worker for the bot to operate fully.

### Commands Folder
This repo has one called `example`, this folder does not have to reside within this repo and can be located anywhere on the system. This path **must** be passed in using the `-c` arg with running `main.py`

The class in these files takes 1 arg in its `__init__` function called `utils`.
`utils` has access to the following data accessed by `utils.some_var`:
- `is_worker`: Boolean value to denote if the instance is a worker or not
- `BOT_NAME`: The bot name formated using `<@BOT_ID>` to be used in messages or command regex's

`utils` also has access to these but most likely not needed in the command class:
- `CONFIG`: The dict read in from `config.yaml`
- `BOT_ID`: The bot slack id
- `slack_client`: Full access to the slackclient commands
- `channels`: Dict of all the channels and their data. The keys are the channel ids as well as the channel names
- `users`: Dict of all the users and their data. The keys are the user ids as well as the user names
- `ims`: Dict of all the direct messages and their data. The keys are the direct messages ids only
- `mq`: The message queue from `pika`, set using `connection.channel()`


#### Command function return values
Return a dict with as many or as few of these keys as needed (if a blank dict is passed, nothing will be posted):
- `text`: String that will be posted
- `attachments`: List of dict(s), Check the slack api docs on how to format the dict
- `thread_reply`: `Boolean` - _Default: `False`_. Set to `True` to repsond to the users command in a thread.
- `add_to_queue`: `Boolean` - _Default: `False`_. Set to `True` to send the task to be process by the workers. Not used if the task is being processed by a worker
- Any other value that the slack `api_call` call takes can also be passed in.
