#!/usr/bin/python
# -*- coding: utf-8 -*-

# TODO: nettoyer les imports...
import os
import yaml
import md5
import re
import urllib2

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
    backend = DummyBackend()
    for user in client.users:
        user.save_documents(backend)

    exit(0)
    client = Client(configuration)
    client.authorize(User('po'))
    x = client.request('https://doc-00-98-docs.googleusercontent.com/docs/securesc/a5epmbk8m5skpnqjcie5urtcndo5cmch/qsaamokok54olbei8hdeom3dd4oar1v4/1350144000000/16822974865821098555/16822974865821098555/0B3poZA2SBKWfaDM4blhCNkYzQ3M?h=15833941256266245015&e=download&gd=true')
    headers = x[0]
    print x
    cd = headers['content-disposition']
    print cd
    print type(cd)
    print [x for x in [0,1]]
    exit(1)
    print type(x)
    print x
    y = client.request('https://docs.google.com/feeds/download/presentations/Export?id=1JurOOdZVPYBkS6zOYbVK8vE8B6QPK3RV3lwCLRfCrXY&exportFormat=pptx')
    print type(y)
    print y
    m = md5.new()
    m.update(y[1])
    print m.hexdigest()
if __name__ == '__main__':
    main()