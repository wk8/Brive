# -*- coding: utf-8 -*-

import yaml

from briveexception import *


class Configuration:

    def __init__(self, settings_file, constants_file):
        self.__data = dict()
        self.__load_from_yml(settings_file)
        self.__load_from_yml(constants_file)

    def __str__(self):
        return str(self.__data)

    # retrives one or several parameters from the current configuration
    # the only possible named parameter is not_null which will make this method
    # raise an exception if the parameter is not found
    # is_int or is_bool can be used to cast the result to the desired type
    def get(self, *args, **kwargs):
        if not args:
            return None
        if len(args) == 1:
            name = args[0]
            if type(name) is str:
                if name in self.__data:
                    result = self.__data[name]
                    if 'is_int' in kwargs and kwargs['is_int']:
                        return int(result)
                    if 'is_bool' in kwargs and kwargs['is_bool']:
                        return result[0].lower() in ('t', '1')
                    return result
                if 'not_null' in kwargs and kwargs['not_null']:
                    raise BriveException(
                        'Missing required configuration parameter: {}'
                        .format(name)
                    )
                return None
            raise Exception(
                'Invalid argument for Configuration.get: {}'.format(repr(name))
            )
        return [self.get(name, **kwargs) for name in args]

    def __add_dict(self, dictionary, prefix=''):
        if prefix:
            prefix += '_'
        for key, value in dictionary.items():
            if type(value) is dict:
                self.__add_dict(value, prefix + key)
            elif type(value) is str or type(value) is list:
                self.__data[prefix + key] = value

    def __load_from_yml(self, yml_file):
        try:
            stream = open(yml_file)
            dictionary = yaml.load(stream)
            self.__add_dict(dictionary)
            stream.close()
        except IOError as io_error:
            raise BriveException(io_error)
        except YAMLError as yaml_error:
            raise BriveException(yaml_error)
