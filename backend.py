# -*- coding: utf-8 -*-

import os
import errno
import time

from briveexception import *
from notifier import *


# a helper class for actual backends
class BaseBackend(object):

    def __init__(self, config):
        self.root_dir = config.get('backend_root_dir', not_null=True)
        # add a trailing slash to root_dir if there isn't any
        self.root_dir += '' if self.root_dir[-1] == os.sep else os.sep

    # can be overriden for more elaborate backends
    def need_to_fetch_contents(self, user, document):
        return True

    # equivalent to *nix's _mkdir -p
    def _mkdir(self, path):
        try:
            os.makedirs(self.root_dir + path)
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                pass
            else:
                raise

    @staticmethod
    def _get_session_dir_name():
        return time.strftime('%Y-%m-%dT%H%M%SZ', time.gmtime())


# doens't do anything, just say it was asked to save, mainly for debugging purposes
class DummyBackend(BaseBackend):

    def save(self, user, document):
        print 'Backend save for user {}: {}'.format(user, repr(document))


# simplest backend possible: just download everything
class SimpleBackend(BaseBackend):

    def __init__(self, config):
        super(SimpleBackend, self).__init__(config)
        # create the root directory for this session: UTC ISO-8601 time
        new_root = BaseBackend._get_session_dir_name()
        self._mkdir(new_root)
        self.root_dir += new_root + os.sep
        debug('SimpleBackend loaded')

    def save(self, user, document):
        self._mkdir(user.login)
        prefix = self.root_dir + user.login + os.sep
        for file_name, content in document.contents.items():
            file_path = prefix + file_name
            debug ('Writing {}\'s {} to {}'.format(
                user.login, document.title, file_path
            ))
            f = open(file_path, 'w')
            f.write(content)
            f.close()



