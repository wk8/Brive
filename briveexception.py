# -*- coding: utf-8 -*-


class BriveException(Exception):

    # receives either a string (with an additional optional
    # string as a short description), or another exception
    def __init__(self, *args):
        if args and type(args[0]) is str:
            super(BriveException, self).__init__()
            self.__message = args[0]
            if len(args) != 1:
                self.__short_description = args[1]
            else:
                self.__short_description = None
        elif args and isinstance(args[0], Exception):
            self.__init__(str(args[0]))
        else:
            raise Exception('Incorrect arguments in BriveException.__init__()')

    def __str__(self):
        return self.__message
