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
    parser.add_argument('--keep-on-crash', dest='keep_on_crash',
                        action='store_const', const=True, default=False,
                        help='By default, we delete all the files if an error '
                        'occurs. Use that flag to keep whatever files have '
                        'been saved so far in the event of an error')
    parser.add_argument('--preferred-formats', dest='preferred_formats',
                        metavar='extension', type=str, nargs='+', default=[],
                        help='When several formats are available, if one (or '
                        'more) of them is in this list, only this (or those)'
                        'format(s) will be downloaded')
    parser.add_argument('--exclusive-formats', dest='exclusive_formats',
                        metavar='extension', type=str, nargs='+', default=[],
                        help='Only files matching those formats will '
                        'get downloaded')
    args = parser.parse_args()

    if args.docs and len(args.users) != 1:
        sys.stderr.write('Incorrect input, use -h for more help\n')
        exit(1)

    # load the logger functions
    Log.init(args.verbose, args.debug)

    backend = None
    try:
        # build the config
        configuration = Configuration(SettingsFiles.SETTINGS_FILE,
                                      SettingsFiles.CONSTANTS_FILE)
        configuration.merge('formats_preferred', args.preferred_formats)
        configuration.merge('formats_exclusive', args.exclusive_formats)
        # check all the formats begin with a leading dot
        preferred_formats = [fmt if fmt[0] == '.' else '.' + fmt
                             for fmt in Configuration.get('formats_preferred')]
        exclusive_formats = [fmt if fmt[0] == '.' else '.' + fmt
                             for fmt in Configuration.get('formats_exclusive')]
        Configuration.set('formats_preferred', preferred_formats)
        Configuration.set('formats_exclusive', exclusive_formats)

        # down to business
        client = Client()
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
    except BaseException as ex:
        if backend:
            try:
                if args.keep_on_crash:
                    backend.finalize()
                else:
                    backend.clean_up()
            except:
                pass
        if hasattr(ex, 'brive_explanation'):
            print u'### {} ###'.format(ex.brive_explanation)
        raise


if __name__ == '__main__':
    main()
