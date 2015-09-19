# -*- coding: utf-8 -*-

import yaml


from backend import *


class Configuration(object):

    instance = None

    def __init__(self, settings_file, constants_file):
        self._data = dict()
        self._load_from_yml(constants_file)
        self._load_from_yml(settings_file)
        Configuration.instance = self
        Log.debug('Configuration loaded')

    def __str__(self):
        return str(self._data)

    # retrives one or several parameters from the current configuration
    # the only possible named parameter is not_null which will make this method
    # raise an exception if the parameter is not found
    # is_int or is_bool can be used to cast the result to the desired type
    @classmethod
    def get(cls, *args, **kwargs):
        instance = Configuration.instance
        if not args:
            return None
        if len(args) == 1:
            name = args[0]
            if type(name) is str:
                if name in instance._data:
                    result = instance._data[name]
                    if 'is_int' in kwargs and kwargs['is_int']:
                        return int(result)
                    if 'is_bool' in kwargs and kwargs['is_bool']:
                        return result[0].lower() in ('t', '1')
                    return result
                if 'not_null' in kwargs and kwargs['not_null']:
                    raise Exception(
                        u'Missing required configuration parameter: {}'
                        .format(name)
                    )
                return None
            raise Exception(
                u'Invalid argument for Configuration.get: {}'
                .format(repr(name))
            )
        return [instance.get(name, **kwargs) for name in args]

    @classmethod
    def set(self, name, value):
        Configuration.instance._data[name] = value

    # used for list and dict values, to update while keeping old entries
    @classmethod
    def merge(self, name, value):
        instance = Configuration.instance
        if name in instance._data:
            current = instance._data[name]
            if type(value) is list and type(current) is list:
                Configuration.set(
                    name, list(set(current) - set(value))
                )
            elif type(value) is dict and type(current) is dict:
                Configuration.set(name, current.update(value))
            else:
                raise Exception(
                    u'Unexpected type in Configuration: {} '.format(type(value)) +
                    u'while previous type was: {}'.format(type(current))
                )
        else:
            Configuration.set(name, value)

    # returns the right backend depending on the configuration
    def get_backend(self, keep_dirs):
        compression = self.get('backend_compression', is_bool=True)
        class_name = self.get('factories_tar_backend', not_null=True) \
            if compression else self.get(
                'factories_simple_backend', not_null=True
            )
        class_object = eval(class_name)
        return class_object(keep_dirs)

    def _add_dict(self, dictionary, prefix=''):
        if prefix:
            prefix += '_'
        for key, value in dictionary.items():
            if type(value) is dict:
                self._add_dict(value, prefix + key)
            elif type(value) is str or type(value) is list:
                self._data[prefix + key] = value

    def _load_from_yml(self, yml_file):
        stream = open(yml_file)
        dictionary = yaml.load(stream)
        self._add_dict(dictionary)
        stream.close()
