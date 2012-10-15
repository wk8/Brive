# -*- coding: utf-8 -*-


class ExpiredTokenException(Exception):
    pass

import feedparser

from httplib2 import Http
from OpenSSL.crypto import Error as CryptoError
from oauth2client.client import *
from apiclient.discovery import build

from briveexception import *
from configuration import *
from backend import *
from model import *
from notifier import *

class Credentials:

    def __init__(self, config, http):
        self._email, p12_file, self._p12_secret, self._scopes = \
            config.get('google_app_email', 'google_app_p12_file',
                       'google_app_p12_secret', 'google_api_scopes',
                       not_null=True)
        try:
            stream = open(p12_file, 'r')
            self._p12 = stream.read()
            stream.close()
        except IOError as io_error:
            raise BriveException(io_error)
        # check our credentials are those of a valid app
        self._valid(http, True)

    # returns true iff the credentials are from a valid Google API app
    # that's quite independent of the domain
    # throw_excptns set to True will throw BriveExceptions instead of
    # just returning false
    def _valid(self, http, throw_excptns=False):
        try:
            signed_assertion = self.get_signed_assertion()
            signed_assertion.refresh(http)
            debug('App\'s credentials valid')
            return True
        except CryptoError as crypto_error:
            if throw_excptns:
                raise BriveException('Incorrect p12 file and/or password ({})'
                                     .format(str(crypto_error)))
        except AccessTokenRefreshError as oauth_error:
            if throw_excptns:
                raise BriveException('Invalid app credentials ({})'.
                                     format(str(oauth_error)))
        return False

    def get_signed_assertion(self, **kwargs):
        return SignedJwtAssertionCredentials(self._email,
                                             self._p12,
                                             self._scopes,
                                             self._p12_secret,
                                             **kwargs)


class Client:

    # FIXME: check extended scopes, and see that we fail,
    # otherwise issue a warning
    def __init__(self, config):
        self._reset()
        self._creds = Credentials(config, self._http)
        self._domain, admin_login, users_api_endpoint = \
            config.get('google_domain_name', 'google_domain_admin_login',
                       'google_api_users_endpoint', not_null=True)
        self._admin = User(admin_login, self)
        self._users_api_endpoint = \
            users_api_endpoint.format(domain_name=self._domain)
        self._curent_user = None
        debug('Client loaded')

    # authorizes the given user
    def authorize(self, user):
        debug('Authorizing client for {}'.format(user.login))
        self._reset()
        signed_assertion = self._creds.get_signed_assertion(
            prn=self._get_email_address(user)
        )
        signed_assertion.authorize(self._http)
        self._curent_user = user

    def reauthorize(self):
        if self._current_user:
            self.authorize(self._current_user)

    def build_service(self, service_name, api_version):
        return build(service_name, api_version, self._http)

    # retrieve the list of all users on the domain
    @property
    def users(self):
        try:
            self.authorize(self._admin)
            headers, xml = self.request(self._users_api_endpoint)
            status = int(headers['status'])
            if status == 200:
                data = feedparser.parse(xml)
                result = [User(user['title'], self) for user in data['entries']]
                verbose('Found users: {}'.format(result))
                return result
            elif status == 403:
                raise BriveException('User {} is not an admin'.
                                     format(self._admin.login))
            else:
                raise BriveException(
                    'Unexpected HTP status when requesting users\' list' +
                    ': {}\nResponse: {}'.format(status, xml))
        except AccessTokenRefreshError as oauth_error:
            raise BriveException(
                'App not authorized on {}'.format(self._domain) +
                '(or your admin user doesn\'t exist) ({})'.format(oauth_error))

    def request(self, *args, **kwargs):
        return self._http.request(*args, **kwargs)

    def _get_email_address(self, user):
        return '{}@{}'.format(user.login, self._domain)

    def _reset(self):
        self._http = Http()
