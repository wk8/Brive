# -*- coding: utf-8 -*-

from briveexception import *

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
        self.__root_dir = config.get('backend_root_dir', not_null=True)
        self.__compress = config.get('backend_compress', is_bool=True)

    def need_to_fetch_contents(self, user, document):
        return True
        
    