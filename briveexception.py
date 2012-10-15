# -*- coding: utf-8 -*-


class BriveException(Exception):

    # receives either a string (with an additional optional
    # string as a short description), or another exception
    def __init__(self, *args):
        if args and type(args[0]) is str:
            super(BriveException, self)._init_()
            self._message = args[0]
            if len(args) != 1:
                self._short_description = args[1]
            else:
                self._short_description = None
        elif args and isinstance(args[0], Exception):
            self._init_(str(args[0]))
        else:
            raise Exception('Incorrect arguments in BriveException.__init__()')

    def __str__(self):
        return self._message
