#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import argparse

# set some constants
SETTINGS_FILE = 'settings.yml'
CONSTANTS_FILE = 'constants.yml'

# argument processing
parser = argparse.ArgumentParser(
    description='Backup all your Google Apps domain\'s users\'s Drive docs.'
)
parser.add_argument('-v', dest='VERBOSE', action='store_const',
                    const=True, default=False, help='Verbose mode')
parser.add_argument('-d', dest='DEBUG', action='store_const',
                    const=True, default=False, help='Debug mode')
args = parser.parse_args()


# define some logging functions
def pprint(*args):
    timestamp = time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
    for arg in args:
        print '[ {} ] '.format(timestamp) + arg

verbose = pprint if args.VERBOSE or args.DEBUG else lambda *args: None
debug = pprint if args.DEBUG else lambda *args: None

# local imports
from configuration import *
from client import *
from model import *
from backend import *


def main():
    try:
        configuration = Configuration(SETTINGS_FILE, CONSTANTS_FILE)
        client = Client(configuration)
        backend = configuration.get_backend()
        for user in client.users:
            user.save_documents(backend)
        backend.finalize()
    except Exception as e:
        backend.clean_up()
        sys.stderr.write(str(e))
        exit(1)


if __name__ == '__main__':
    main()
