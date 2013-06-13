# -*- coding: utf-8 -*-


class ExpiredTokenException(Exception):
    pass


class FailedRequestException(Exception):
    pass


class ExpectedFailedRequestException(Exception):
    pass

import feedparser

import streaming_httplib2
from httplib2 import Http as StandardHttp
from OpenSSL.crypto import Error as CryptoError
from oauth2client.client import \
    SignedJwtAssertionCredentials, AccessTokenRefreshError
from apiclient.discovery import build

from model import User, Document, Folder
from utils import *
from configuration import Configuration


# just reverts to default httplib2 behavior unless
# explicitely required (comes in handy to still use
# Google's code with streaming_httplib2.Http objects)
class StreamingHttp(streaming_httplib2.Http):

    def __init__(self, *args, **kwargs):
        self._use_streaming = False
        super(StreamingHttp, self).__init__(*args, **kwargs)

    def request(self, *args, **kwargs):
        headers, content = super(StreamingHttp, self).request(*args, **kwargs)
        if not self._use_streaming:
            content = content.read()
        return (headers, content)

    # should be a keyword arg, but that doesn't sit too well
    # with google's wrapping...
    def use_streaming(self, value=True):
        self._use_streaming = value


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
    def __init__(self, keep_dirs, streaming):
        self._keep_dirs = keep_dirs
        self._streaming = streaming
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
        self._admin = User(admin_login, self, False)
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
    def streaming(self):
        return self._streaming

    @property
    def drive_service(self):
        return self.build_service(self._drv_svc_name, self._drv_svc_version)

    # retrieve the list of all users on the domain
    @property
    def users(self):
        try:
            self.authorize(self._admin)
            user_logins = self._get_all_user_logins()
            result = [User(login, self, self._keep_dirs)
                      for login in user_logins]
            Log.verbose(u'Found users: {}'.format(result))
            return result
        except AccessTokenRefreshError as oauth_error:
            explanation = \
                u'App not authorized on {}'.format(self._domain) \
                + '(or your admin user doesn\'t exist)'
            oauth_error.brive_explanation = explanation
            raise

    # returns a list of users, on the current page
    def _get_single_user_page(self, start_username=None):
        url = self._users_api_endpoint
        url += ('?startUsername=' + start_username) if start_username else ''
        try:
            headers, xml = self.request(
                url, brive_expected_error_status=403
            )
            data = feedparser.parse(xml)
            return [user['title'] for user in data['entries']]
        except ExpectedFailedRequestException:
            raise Exception(u'User {} is not an admin'
                            .format(self._admin.login))

    # gets the complete list of users
    def _get_all_user_logins(self):
        result = set()
        current_list = []
        previous_last_login = None
        current_last_login = None
        while current_last_login is None\
                or current_last_login != previous_last_login:
            previous_last_login = current_last_login
            current_list = self._get_single_user_page(current_last_login)
            current_last_login = current_list[-1]
            result.update(current_list)
        result = list(result)
        result.sort()
        return result

    @Utils.multiple_tries_decorator(ExpectedFailedRequestException)
    def request(self, *args, **kwargs):
        # pop a few internal kwargs
        expected_error_status = kwargs.pop('brive_expected_error_status', [])
        if not isinstance(expected_error_status, list):
            expected_error_status = [expected_error_status]
        if kwargs.pop('brive_streaming', False) and self._streaming:
            self._http.use_streaming()

        result = self._http.request(*args, **kwargs)

        if self._streaming:
            self._http.use_streaming(False)
        headers = result[0]
        status = int(headers.get('status', 0))
        if status != 200:
            if status in expected_error_status:
                raise ExpectedFailedRequestException(status)
            else:
                content = result[1]
                if self._streaming:
                    content = content.read()
                raise FailedRequestException(
                    u'Http request failed (return code: {}, headers: {} '
                    .format(status, headers)
                    + u'and content: {})'.format(content.decode('utf8'))
                )
        return result

    def _get_email_address(self, user):
        return '{}@{}'.format(user.login, self._domain)

    def _reset(self):
        if self._streaming:
            self._http = StreamingHttp()
        else:
            self._http = StandardHttp()


class UserDocumentsGenerator:

    def __init__(self, user, query=None, cls=Document):
        self._user = user
        # the query is used for the requests to the API
        # (see doc @ https://developers.google.com/drive/search-parameters)
        self._query = query
        self._class = cls

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
        self._current_page = []
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
            if self._query:
                kwargs['q'] = self._query
            response = self._drive_service.files().list(**kwargs).execute()
            self._current_page_token = self._next_page_token
            self._next_page_token = response.get('nextPageToken')
            self._current_page_nb += 1
            items = response['items']
            Log.debug('Retrieving page # {} of docs : found {} documents'
                      .format(self._current_page_nb, len(items)))
            self._current_page = [
                self._class(meta, self._user.folders) for meta in items
                if meta['id'] not in self._already_done_ids
            ]
        else:
            self._current_page = []
        # no need to keep the processed ids of the current page in memory
        self._already_done_ids = []
