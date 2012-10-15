# -*- coding: utf-8 -*-

import os
import time

from briveexception import *
from notifier import *

# doens't do anything, just say it was asked to save, mainly for debugging purposes
class DummyBackend:

    def need_to_fetch_contents(self, user, document):
        return True

    def save(self, user, document):
        print 'Backend save for user {}: {}'.format(user, repr(document))


# simplest backend possible: just download everything
# (with an optional compression)
class SimpleBackend:

    def __init__(self, config):
        self.__compress = config.get('backend_compress', is_bool=True)
        self.__root_dir = config.get('backend_root_dir', not_null=True)
        # add a trailing slash to root_dir if there isn't any
        self.__root_dir += '' if self.__root_dir[-1] == os.sep else os.sep
        # create the root directory for this session: UTC ISO-8601 time
        new_root = time.strftime('%Y-%m-%dT%H%M%SZ', time.gmtime())
        self.__mkdir(new_root)
        self.__root_dir = new_root + os.sep

    def need_to_fetch_contents(self, user, document):
        return True

    def save(self, user, document):
        # TODO log...
        self.__mkdir(user.login)
        prefix = self.__root_dir + user.login + os.sep
        for file_name, content in document.contents.items():
            f = open(prefix + file_name, 'r')
            f.write(content)
            f.close()

    # equivalent to *nix's mkdir -p
    def __mkdir(self, path):
        try:
            os.makedirs(self.__root_dir + path)
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                pass
            else:
                raise

