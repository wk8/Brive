# -*- coding: utf-8 -*-

import time
import sys


class SettingsFiles:

    SETTINGS_FILE = r'settings.yml'
    CONSTANTS_FILE = r'constants.yml'


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
    def error(*args):
        sys.stderr.write(Log._timestamped_string(*args))

    @staticmethod
    def _timestamped_string(*args):
        timestamp = time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
        return u'[ {} ] '.format(timestamp) + args[0]

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
