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
                        type=str, nargs='+', default=[],
                        help='Custom logins instead of all of them')
    parser.add_argument('--docs', dest='docs', metavar='doc_id',
                        type=str, nargs='+', default=None,
                        help='Custom doc ids to retrieve (in which case you'
                        ' must also give the login of exaclty one user owning'
                        ' those docs (using the -u flag))')
    args = parser.parse_args()

    if args.docs and len(args.users) != 1:
        sys.stderr.write('Incorrect input, use -h for more help\n')
        exit(1)

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
        if args.docs:
            # sepecific doc_ids, only one user
            user = users[0]
            for doc_id in args.docs:
                user.retrieve_single_document(backend, doc_id)
        else:
            # general use case
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
