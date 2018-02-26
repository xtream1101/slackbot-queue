import os
import yaml
from celery import Celery


config = yaml.load(open(os.environ['SB_CONFIG'], 'r'))

app = Celery('slackbot',
             broker='amqp://{USER}:{PASSWORD}@{HOST}:5672/{VHOST}'.format(**config['RABBITMQ']),
             backend='rpc://',
             include=['slackbot.tasks'])

app.conf.task_default_queue = config['RABBITMQ']['QUEUE_NAME']
