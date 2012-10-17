# -*- coding: utf-8 -*-


class ExpiredTokenException(Exception):
    pass

import feedparser

from httplib2 import Http
from OpenSSL.crypto import Error as CryptoError
from oauth2client.client import *
from apiclient.discovery import build

from configuration import *
from backend import *
from model import *
from brive import *


class Credentials:

    def __init__(self, config, http):
        self._email, p12_file, self._p12_secret, self._scopes = \
            config.get('google_app_email', 'google_app_p12_file',
                       'google_app_p12_secret', 'google_api_scopes',
                       not_null=True)
        stream = open(p12_file, 'r')
        self._p12 = stream.read()
        stream.close()
        # check our credentials are those of a valid app
        self._valid(http, True)

    # returns true iff the credentials are from a valid Google API app
    # that's quite independent of the domain
    # throw_excptns set to True will throw Exceptions instead of
    # just returning false
    def _valid(self, http, throw_excptns=False):
        try:
            signed_assertion = self.get_signed_assertion()
            signed_assertion.refresh(http)
            Log.debug('App\'s credentials valid')
            return True
        except CryptoError as crypto_error:
            if throw_excptns:
                crypto_error.brive_explanation = \
                    'Incorrect p12 file and/or password'
                raise
        except AccessTokenRefreshError as oauth_error:
            if throw_excptns:
                oauth_error.brive_explanation = 'Invalid app credentials'
                raise
        return False

    def get_signed_assertion(self, **kwargs):
        return SignedJwtAssertionCredentials(self._email,
                                             self._p12,
                                             self._scopes,
                                             self._p12_secret,
                                             **kwargs)


class Client:

    # if a request fails, we'll re-try it that many times at most
    _max_request_tries = 3

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
        Log.debug('Client loaded')

    # authorizes the given user
    def authorize(self, user):
        Log.debug(u'Authorizing client for {}'.format(user.login))
        self._reset()
        signed_assertion = self._creds.get_signed_assertion(
            prn=self._get_email_address(user)
        )
        signed_assertion.authorize(self._http)

    def build_service(self, service_name, api_version):
        return build(service_name, api_version, self._http)

    # retrieve the list of all users on the domain
    @property
    def users(self):
        try:
            self.authorize(self._admin)
            headers, xml = self.request(
                self._users_api_endpoint, brive_check_status=False
            )
            status = int(headers['status'])
            if status == 200:
                data = feedparser.parse(xml)
                result = [User(user['title'], self)
                          for user in data['entries']]
                Log.verbose(u'Found users: {}'.format(result))
                return result
            elif status == 403:
                raise Exception(u'User {} is not an admin'
                                .format(self._admin.login))
            else:
                raise Exception(
                    'Unexpected HTP status when requesting users\' list'
                    + u': {}\nResponse: {}'.format(status, xml))
        except AccessTokenRefreshError as oauth_error:
            explanation = \
                u'App not authorized on {}'.format(self._domain) \
                + '(or your admin user doesn\'t exist)'
            oauth_error.brive_explanation = explanation
            raise

    def request(self, *args, **kwargs):
        try_nb = kwargs.pop('brive_try_nb', 1)
        check_status_code = kwargs.pop('brive_check_status', True)
        try:
            result = self._http.request(*args, **kwargs)
            if check_status_code:
                headers = result[0]
                status = int(headers['status'])
                if status != 200:
                    raise Exception(
                        u'Http request failed (return code: {})'.format(status)
                    )
            return result
        except Exception:
            if try_nb >= Client._max_request_tries:
                raise
            kwargs.update({
                'brive_try_nb': try_nb + 1,
                'brive_check_status': check_status_code
            })
            return self.request(*args, **kwargs)

    def _get_email_address(self, user):
        return '{}@{}'.format(user.login, self._domain)

    def _reset(self):
        self._http = Http()
