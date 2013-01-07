# -*- coding: utf-8 -*-


class ExpiredTokenException(Exception):
    pass


class FailedRequestException(Exception):
    pass

import feedparser

from httplib2 import Http
from OpenSSL.crypto import Error as CryptoError
from oauth2client.client import \
    SignedJwtAssertionCredentials, AccessTokenRefreshError
from apiclient.discovery import build

from model import User, Document
from utils import *
from configuration import Configuration


class Credentials:

    def __init__(self, http):
        self._email, p12_file, self._p12_secret, self._scopes = \
            Configuration.get('google_app_email', 'google_app_p12_file',
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

    # FIXME: check extended scopes, and see that we fail,
    # otherwise issue a warning
    def __init__(self):
        self._reset()
        self._creds = Credentials(self._http)
        self._domain, admin_login, users_api_endpoint, \
            self._drv_svc_name, self._drv_svc_version = \
            Configuration.get('google_domain_name',
                              'google_domain_admin_login',
                              'google_api_users_endpoint',
                              'google_api_drive_name',
                              'google_api_drive_version',
                              not_null=True)
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

    @property
    def drive_service(self):
        return self.build_service(self._drv_svc_name, self._drv_svc_version)

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

    @Utils.multiple_tries_decorator(None)
    def request(self, *args, **kwargs):
        check_status_code = kwargs.pop('brive_check_status', True)
        result = self._http.request(*args, **kwargs)
        if check_status_code:
            headers = result[0]
            status = int(headers['status'])
            if status != 200:
                raise FailedRequestException(
                    u'Http request failed (return code: {}, headers: {} '
                    .format(status, headers)
                    + u'and content: {})'.format(result[1].decode('utf8'))
                )
        return result

    def _get_email_address(self, user):
        return '{}@{}'.format(user.login, self._domain)

    def _reset(self):
        self._http = Http()


class UserDocumentsGenerator:

    def __init__(self, user):
        self._user = user

    def __iter__(self):
        self._current_page_nb = 0
        self._current_page = []
        self._current_page_token = None
        self._next_page_token = None
        self._drive_service = None
        self._already_done_ids = []
        return self

    @Utils.multiple_tries_decorator([ExpiredTokenException, StopIteration])
    def next(self):
        return self._get_next_doc()

    def add_processed_id(self, doc_id):
        self._already_done_ids.append(doc_id)

    def reset_to_current_page(self):
        self._next_page_token = self._current_page_token
        self._current_page_nb -= 1

    def _get_next_doc(self, first_try=True):
        try:
            if not first_try or not self._drive_service:
                # we need to re-auth
                self._drive_service = self._user.drive_service
            return self._do_get_next_doc()
        except ExpiredTokenException:
            if first_try:
                # let's try again
                return self._get_next_doc(False)
            raise Exception(
                'Two oauth errors in a row while processing'
                + u'{}\'s documents '.format(self._user.login)
                + 're-authentication failed'
            )

    def _do_get_next_doc(self):
        if not self._current_page:
            self._fetch_next_page()
        try:
            return self._current_page.pop(0)
        except IndexError:
            # no more docs to be fetched
            raise StopIteration

    def _fetch_next_page(self):
        if not self._current_page_nb or self._next_page_token:
            kwargs = {}
            if self._next_page_token:
                kwargs['pageToken'] = self._next_page_token
            response = self._drive_service.files().list(**kwargs).execute()
            self._current_page_token = self._next_page_token
            self._next_page_token = response.get('nextPageToken')
            self._current_page_nb += 1
            items = response['items']
            Log.debug('Retrieving page # {} of docs : found {} documents'
                      .format(self._current_page_nb, len(items)))
            self._current_page = [Document(meta) for meta in items
                                  if meta['id'] not in self._already_done_ids]
        else:
            self._current_page = []
        # no need to keep the processed ids of the current page in memory
        self._already_done_ids = []
