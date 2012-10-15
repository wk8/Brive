# -*- coding: utf-8 -*-

import time

def pprint(*args):
    timestamp = time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
    for arg in args:
        print '[ {} ] '.format(timestamp) + arg

# TODO
verbose = pprint if True else lambda *args: None
debug = pprint if True else lambda *args: None
