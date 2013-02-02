#!/usr/bin/python
# -*- coding: utf-8 -*-

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
    parser.add_argument('--list', dest='list',
                        action='store_const', const=True, default=False,
                        help='List all doc ids found for one user, then exit '
                        '(as for --docs you must also give the login of '
                        'exaclty one user)')
    parser.add_argument('--keep-on-crash', dest='keep_on_crash',
                        action='store_const', const=True, default=False,
                        help='By default, we delete all the files if an error '
                        'occurs. Use that flag to keep whatever files have '
                        'been saved so far in the event of an error')
    parser.add_argument('--preferred-formats', dest='preferred_formats',
                        metavar='extension', type=str, nargs='+', default=[],
                        help='When several formats are available, if one (or '
                        'more) of them is in this list, only this (or those)'
                        ' format(s) will be downloaded')
    parser.add_argument('--exclusive-formats', dest='exclusive_formats',
                        metavar='extension', type=str, nargs='+', default=[],
                        help='Only files matching those formats will '
                        'get downloaded (note that some other related '
                        'formats may be downloaded as well as this is based on'
                        ' Python\'s mimetypes package)')
    parser.add_argument('--user-list', dest='user_list',
                        action='store_const', const=True, default=False,
                        help='List all users found on the domain, then exit')
    parser.add_argument('--owned-only', dest='owned_only',
                        action='store_const', const=True, default=False,
                        help='If activated, only documents owned by the '
                        'user(s) will be downloaded (except if a not-owned doc'
                        'is explictely required with --docs)')
    args = parser.parse_args()

    # load the logger functions
    Log.init(args.verbose, args.debug)

    if (args.docs or args.list) and len(args.users) != 1:
        Log.error('Incorrect input, aborting. Please use -h for more help')
        exit(1)

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
        users = [User(login, client) for login in args.users] if args.users \
            else client.users

        if args.user_list:
            # just display the list of all the users, then exit
            print users
            return

        if args.list:
            # just display the list of doc ids for that user, and exit
            print users[0].document_ids
            return

        # usual use case : retrieve the docs
        backend = configuration.get_backend()
        if args.docs:
            # sepecific doc_ids, only one user
            for doc_id in args.docs:
                users[0].retrieve_single_document(backend, doc_id)
        else:
            # general use case
            for user in users:
                user.save_documents(backend, args.owned_only)

        Log.verbose('All successful, finalizing backend...')
        backend.finalize()
    except BaseException as ex:
        if backend:
            try:
                if args.keep_on_crash:
                    Log.verbose(
                        'Unexpected shutdown, trying to finalize backend...'
                        + ' (you selected --keep-on-crash)'
                    )
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
