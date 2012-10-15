#!/usr/bin/python
# -*- coding: utf-8 -*-

# TODO: nettoyer les imports...
import os
import yaml
import md5
import re
import urllib2
import time

class Options:
    pass

Options.BRIVE_DEBUG = True
Options.BRIVE_VERBOSE = True

from briveexception import *
from configuration import *
from client import *
from model import *
from backend import *

SETTINGS_FILE = 'settings.yml'
CONSTANTS_FILE = 'constants.yml'

def main():

    configuration = Configuration(SETTINGS_FILE, CONSTANTS_FILE)
    client = Client(configuration)
    backend = configuration.get_backend()
    for user in client.users:
        user.save_documents(backend)
    backend.finalize()


if __name__ == '__main__':
    main()