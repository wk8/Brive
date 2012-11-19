# -*- coding: utf-8 -*-

import time
import sys
import traceback
import os


class SettingsFiles:
    base_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep
    SETTINGS_FILE = base_dir + r'settings.yml'
    CONSTANTS_FILE = base_dir + r'constants.yml'


class Utils:

    # if a try fails, we'll re-try it that many times at most
    _max_nb_tries = 3

    @staticmethod
    def multiple_tries_decorator(blacklist):
        if blacklist is None:
            blacklist = []
        elif type(blacklist) is not list:
            blacklist = [blacklist]

        def internal_decorator(function):
            def result(*args, **kwargs):
                return Utils._multiple_tries_rec(
                    function, blacklist, 1, *args, **kwargs
                )
            return result
        return internal_decorator

    @staticmethod
    def _multiple_tries_rec(function, blacklist, try_nb, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as ex:
            if type(ex) in blacklist:
                Log.debug(
                    u'Caught a blacklisted {}, re-throwing'.format(type(ex))
                )
                raise
            if try_nb >= Utils._max_nb_tries:
                Log.debug('Too many tries, re-throwing')
                raise
            Log.debug(u'Attempt # {} calling {} failed, re-trying...'
                      .format(try_nb, function.__name__))
            return Utils._multiple_tries_rec(
                function, blacklist, try_nb + 1, *args, **kwargs
            )


class Log:

    @staticmethod
    def error(*args, **kwargs):
        ttstr_kwargs = {'new_line':True, 'with_BT':True}
        ttstr_kwargs.update(kwargs)
        sys.stderr.write(Log._timestamped_string(*args, **ttstr_kwargs))

    @staticmethod
    def _timestamped_string(*args, **kwargs):
        timestamp = time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
        try:
            message = args[0].encode('ascii', 'replace')
            if kwargs.get('with_BT', False):
                message += ' (Traceback (most recent call last): ' \
                    + str(traceback.extract_stack()) + ' )'
            return u'[ {} ] '.format(timestamp) + message \
                + ('\n' if kwargs.get('new_line', False) else '')
        except Exception as ex:
            if not kwargs.get('ignore_errors', False):
                Log.error(
                    'Error when logging! Exception message: ' + str(ex),
                    ignore_errors=True
                )

    @staticmethod
    def init(verbose, debug):
        @staticmethod
        def pprint(*args):
            print Log._timestamped_string(*args)

        @staticmethod
        def void(*args):
            pass
        Log.debug = pprint if debug else void
        Log.verbose = pprint if verbose or debug else void
