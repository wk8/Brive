# -*- coding: utf-8 -*-

import os
import errno
import time
import tarfile
import shutil
import re
from StringIO import StringIO

from utils import *
import configuration


# a helper class for actual backends
class BaseBackend(object):

    def __init__(self, keep_dirs):
        self._root_dir = configuration.Configuration.get(
            'backend_root_dir', not_null=True
        )
        self._keep_dirs = keep_dirs
        self._session_name = self._generate_session_name()

    # can be overriden for more elaborate backends
    def need_to_fetch_contents(self, user, document):
        return True

    # equivalent to *nix's _mkdir -p
    def _mkdir(self, path=''):
        try:
            os.makedirs(os.path.join(self._root_dir, path))
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

    # equivalent to *nix's rm -rf
    def _delete(self, name):
        path = os.path.join(self._root_dir, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)

    def finalize(self):
        pass

    # called to clean up if there was an exception halfway through
    def clean_up(self):
        pass

    # should return the backup dir of file name for that login
    def _get_backup_name_for_user(self, login):
        return login

    # should return the login from a backup dir or file name
    # reverse of _get_backup_name_for_user
    def _get_login_from_name(self, name):
        return name

    # UTC ISO-8601 time
    _UTC_TIME_PATTERN = r'%Y-%m-%dT%H%M%SZ'

    @staticmethod
    def _generate_session_name():
        return time.strftime(BaseBackend._UTC_TIME_PATTERN, time.gmtime())

    @staticmethod
    def _date_from_session_name(name):
        return time.strptime(name, BaseBackend._UTC_TIME_PATTERN)


# doens't do anything, just say it was asked to save
# mainly for debugging purposes
class DummyBackend(BaseBackend):

    def save(self, user, document):
        print u'Backend save for user {}: {}'.format(user, repr(document))


# simplest backend possible: just download everything
class SimpleBackend(BaseBackend):

    def __init__(self, keep_dirs):
        super(SimpleBackend, self).__init__(keep_dirs)
        self._mkdir(self._session_name)
        self._current_dir = os.path.join(self._root_dir, self._session_name)
        Log.debug('SimpleBackend loaded')

    def save(self, user, document):
        path = self._get_path(user, document)
        self._mkdir(os.path.join(self._session_name, path))
        prefix = os.path.join(self._current_dir, path)
        for file_name, content in document.contents.items():
            path = os.path.join(prefix, file_name)
            Log.debug(u'Writing {}\'s {} to {}'.format(
                user.login, document.title, path
            ))
            f = open(path, 'w')
            f.write(content)
            f.close()

    def clean_up(self):
        Log.verbose(u'Unexpected shutdown, deleting {} folder'
                    .format(self._current_dir))
        self._delete(self._session_name)

    def _get_path(self, user, document):
        path = os.path.join(user.login, document.path if self._keep_dirs else '')
        return path

    # returns None if the current name is not a backup dir
    # and the date for this backup if it is
    def _get_backup_date(self, name):
        if os.path.isdir(os.path.join(self._root_dir, name)):
            try:
                return self._date_from_session_name(name)
            except ValueError:
                # not a backup dir!
                pass
        return None

    _SECS_PER_DAY = 86400

    # returns true iff name is a backup dir older than
    # the prescribed # of days
    def _should_delete_old_saves(self, name, days):
        bckup_time = self._get_backup_date(name)
        return bckup_time and time.mktime(self._date_from_session_name(self._session_name)) - time.mktime(bckup_time) > days * self._SECS_PER_DAY

    def _delete_old_saves_in_session(self, session_name, logins):
        current_bckup = os.path.join(self._root_dir, session_name)
        for name in os.listdir(current_bckup):
            login = self._get_login_from_name(name)
            if login and login in logins:
                path_to_del = os.path.join(session_name, name)
                Log.verbose(u'Deleting obsolete path {}'.format(path_to_del))
                self._delete(path_to_del)
        # delete the whole dir if there's nothing left
        try:
            os.rmdir(current_bckup)
            Log.verbose(u'Deleting empty backup dir {}'.format(current_bckup))
        except OSError as ex:
            if ex.errno != errno.ENOTEMPTY:
                raise

    # deletes previous saves for those logins,
    # dating back more than the provided # of days
    def _do_delete_old_saves(self, logins, days):
        for name in os.listdir(self._root_dir):
            if self._should_delete_old_saves(name, days):
                self._delete_old_saves_in_session(name, logins)

    # deletes previous saves for users successfully saved during the current
    # session, whose previous backup is older than the provided # of days
    def delete_old_saves(self, days):
        self._do_delete_old_saves((self._get_login_from_name(name) for name in os.listdir(self._current_dir)), days)


# also downloads everything, but compresses it
class TarBackend(SimpleBackend):

    def __init__(self, keep_dirs):
        super(TarBackend, self).__init__(keep_dirs)
        # get the compression format
        self._format = configuration.Configuration.get(
            'backend_compression_format', not_null=True
        )
        if self._format not in ('gz', 'bz2'):
            raise Exception(
                'The compression format must be either gz or bz2, '
                + u'{} given'.format(format)
            )
        self._tar_files = dict()
        Log.debug('TarBackend loaded')

    # should return the backup dir of file name for that login
    def _get_backup_name_for_user(self, login):
        return login + '.tar.' + self._format

    _login_from_name_regex = re.compile(r'^(.*)\.tar\.(gz|bz2)$')

    # should return the login from a backup dir or file name
    # reverse of _get_backup_name_for_user
    def _get_login_from_name(self, name):
        try:
            return self._login_from_name_regex.findall(name)[0][0]
        except IndexError:
            # no match
            return None

    def save(self, user, document):
        # create the tarfile if we don't have one for this user yet
        if user.login not in self._tar_files:
            name = os.path.join(self._current_dir, self._get_backup_name_for_user(user.login))
            self._tar_files[user.login] = tarfile.open(
                name, 'w:' + self._format
            )
        tar_file = self._tar_files[user.login]
        for file_name, content in document.contents.items():
            path = self._get_path(user, document)
            path = os.path.join(path, file_name)
            Log.debug(u'Writing {}\'s {} to {}'.format(
                user.login, document.title, path
            ))
            file_object = StringIO(content)
            tarnfo = tarfile.TarInfo(path)
            tarnfo.size = file_object.len
            tarnfo.mtime = document.modified_timestamp
            tar_file.addfile(tarnfo, file_object)

    def finalize(self):
        Log.debug('Closing tar files')
        for tar_file in self._tar_files.values():
            tar_file.close()

