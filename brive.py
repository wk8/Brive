#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import argparse


class SettingsFiles:

    SETTINGS_FILE = r'settings.yml'
    CONSTANTS_FILE = r'constants.yml'


class Log:

    @staticmethod
    def verbose(*args):
        pass

    @staticmethod
    def init(verbose, debug):
        @staticmethod
        def pprint(*args):
            timestamp = time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
            for arg in args:
                print u'[ {} ] '.format(timestamp) + arg
        Log.debug = pprint if debug else lambda *args: None
        Log.verbose = pprint if verbose or debug else lambda *args: None

# local imports
from configuration import *
from client import Client
from model import User


def main():
    # argument processing
    parser = argparse.ArgumentParser(
        description='Backup all your Google Apps domain\'s users\'s Drive docs'
    )
    parser.add_argument('-v', dest='verbose', action='store_const',
                        const=True, default=False, help='Verbose mode')
    parser.add_argument('-d', dest='debug', action='store_const',
                        const=True, default=False, help='Debug mode')
    parser.add_argument('-u', dest='users', metavar='login',
                        type=str, nargs='+', default=None,
                        help='Custom logins instead of all of them')
    args = parser.parse_args()

    # load the logger functions
    Log.init(args.verbose, args.debug)

    # down to business
    backend = None
    try:
        configuration = Configuration(SettingsFiles.SETTINGS_FILE,
                                      SettingsFiles.CONSTANTS_FILE)
        client = Client(configuration)
        backend = configuration.get_backend()
        users = [User(login, client) for login in args.users] if args.users \
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
            print u'### {} ###'.format(ex.brive_explanation)
        raise


if __name__ == '__main__':
    main()
