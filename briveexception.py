# -*- coding: utf-8 -*-


class BriveException(Exception):

    # receives either a string, or another exception
    def __init__(self, *args):
        if args and type(args[0]) is str:
            super(BriveException, self).__init__()
            self._message = args[0]
        elif args and isinstance(args[0], Exception):
            self.__init__(str(args[0]))
        else:
            raise Exception('Incorrect arguments in BriveException.__init__()')

    def __str__(self):
        return self._message
