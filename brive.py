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
parser.add_argument('-u', dest='users', metavar='login', type=str, nargs='+',
                    default=None, help='Custom logins instead of all of them')
ARGS = parser.parse_args()


# define some logging functions
def pprint(*args):
    timestamp = time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
    for arg in args:
        print '[ {} ] '.format(timestamp) + arg

verbose = pprint if ARGS.VERBOSE or ARGS.DEBUG else lambda *args: None
debug = pprint if ARGS.DEBUG else lambda *args: None

# local imports
from configuration import *
from client import *
from model import *
from backend import *


def main():
    backend = None

    try:
        configuration = Configuration(SETTINGS_FILE, CONSTANTS_FILE)
        client = Client(configuration)
        backend = configuration.get_backend()
        users = [User(login, client) for login in ARGS.users] if ARGS.users \
            else client.users
        for user in users:
            user.save_documents(backend)
        backend.finalize()
    except Exception as ex:
        if backend:
            try:
                backend.clean_up()
            except:
                pass
        if hasattr(ex, 'brive_explanation'):
            print '### {} ###'.format(ex.brive_explanation)
        raise


if __name__ == '__main__':
    main()
