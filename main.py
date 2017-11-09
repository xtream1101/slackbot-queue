import os
import yaml
import logging
import argparse
from worker import Worker
from listener import Listener

parser = argparse.ArgumentParser(description='Meeseeks Box')
parser.add_argument('-c', '--command-path', help='Path to the folder with commands',
                    nargs='?', required=True)
parser.add_argument('-w', '--worker', action='store_true', help='Set if this instance is a worker')
parser.add_argument('-f', '--config-file', default='config.yaml', help='The name of the config file')
args = parser.parse_args()

config_path = os.path.join(args.command_path, args.config_file)
CONFIG = yaml.load(open(config_path, 'r'))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


if __name__ == '__main__':
    if args.worker is False:
        task = Listener(config=CONFIG, cmd_path=args.command_path, is_worker=False)
    else:
        task = Worker(config=CONFIG, cmd_path=args.command_path, is_worker=True)
