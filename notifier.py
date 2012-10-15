# -*- coding: utf-8 -*-

import time

def pprint(*args):
    for arg in args:
        print '[ {} ] '.format(
            time.strftime('%Y-%m-%d T %H:%M:%S Z', time.gmtime())
        ) + arg

# TODO
verbose = pprint if True else lambda *args: None
debug = pprint if True else lambda *args: None

