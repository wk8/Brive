#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import argparse

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
        ids = ['1ymj9aSlqwerrpwlUJJGFQ7Qb7KIVxBsUBjvlsFE-kpI', '0B-JE-EChYkpMMkRacEs0Wk56Wjg'] # belongs to wk
        u = User('po', client)
        id = ids[1]
        # x = u._do_retrieve_single_document(id)
        # print x
        # exit(1)
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
