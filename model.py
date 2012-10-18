# -*- coding: utf-8 -*-

import md5
import re
from StringIO import StringIO

from client import ExpiredTokenException
from utils import *
from apiclient.errors import HttpError

class User:

    def __init__(self, login, client):
        # check that we have only the login, not the full email address
        if '@' in login:
            login = login.partition('@')[0]
        self._login = login
        self._client = client
        self._documents = None

    def __repr__(self):
        return self._login

    @property
    def login(self):
        return self._login

    @property
    def documents(self):
        if self._documents is None:
            self._fetch_docs_list()
        return self._documents

    @property
    def drive_service(self):
        client = self._client
        client.authorize(self)
        return client.drive_service

    def save_documents(self, backend):
        Log.verbose(u'Processing docs for {}'.format(self.login))
        # list of processed ids
        done = list()
        # keep track of errors that happen twice in a row
        second_error = False
        wk = lambda : self._fetch_docs_list(done)
        wk()
        # self._fetch_docs_list()
        while self._documents:
            document = self._documents.pop()
            Log.verbose(u'Processing {}\'s doc "{}" (id: {})'.format(
                self.login, document.title, document.id
            ))
            try:
                if not backend.need_to_fetch_contents(self, document):
                    # mark as done, and get to the next one
                    Log.verbose(
                        u'Not necessary to fetch doc id '.format(document.id)
                    )
                    done.append(document.id)
                    continue
                document.fetch_contents(self._client)
                second_error = False
            except ExpiredTokenException:
                if second_error:
                    raise Exception(
                        'Two oauth errors in a row while processing'
                        + u'{}\'s documents '.format(self.login)
                        + u'(doc id: {}), '.format(document.id)
                        + 're-authentication failed'
                    )
                else:
                    second_error = True
                    self._fetch_docs_list(done)
                    continue
            except Exception as ex:
                explanation = \
                    'Unexpected error when processing ' \
                    + '{}\'s documents '.format(self.login) \
                    + u'(doc id: {})'.format(document.id)
                ex.brive_explanation = explanation
                raise
            # now we can save it
            self._save_single_document(backend, document)
            # mark as done
            done.append(document.id)

    def retrieve_single_document(self, doc_id):
        try:
            self._do_retrieve_single_document(doc_id)
        except Exception as e:
            explanation = 'Error while retrieving single document id ' \
                + u'{} for user {}, '.format(doc_id, self.login) \
                + 'it\'s liklely this user isn\'t allowed to see that doc'
            e.brive_explanation = explanation
            raise
        document.fetch_contents(self._client)
        self._save_single_document(backend, document)

    @Utils.multiple_tries_decorator(None)
    def _do_retrieve_single_document(self, doc_id):
        return self.drive_service.files().get(fileId=doc_id).execute()

    # fetches the documents' list, except those whose ids are in 'exclude'
    def _fetch_docs_list(self, exclude=list()):
        Log.debug('Fetching doc list for {}'.format(self.login))
        try:
            docs_list = self._do_fetch_docs_list()
        except Exception as e:
            e.brive_explanation = \
                u'Unable to retrieve {}\'s docs list'.format(self.login)
            raise
        self._documents = [Document(meta) for meta in docs_list['items']
                           if meta['id'] not in exclude]

    @Utils.multiple_tries_decorator(None)
    def _do_fetch_docs_list(self):
        return self.drive_service.files().list().execute()

    def _save_single_document(self, backend, document):
        try:
            Log.verbose(u'Saving {}\'s doc "{}" (id: {})'.format(
                self.login, document.title, document.id
            ))
            backend.save(self, document)
        except Exception as ex:
            explanation = \
                'Unexpected error when saving ' \
                + '{}\'s documents '.format(self.login) \
                + u'(doc id: {})'.format(document.id)
            ex.brive_explanation = explanation
            raise
        # no need to keep the potentially big document's contents in memory
        document.del_contents()

class Document:

    _name_from_header_regex = re.compile(r'^attachment;\s*filename="([^"]+)"')
    _split_extension_regex = re.compile(r'\.([^.]+)$')

    def __init__(self, meta):
        self._meta = meta
        self._contents = None

    def __repr__(self):
        result = u'Meta: {}'.format(self._meta)
        if self._contents is None:
            result += '\nNo contents\n'
        else:
            result += u'\nContents: {}\n'.format(self._contents)
        return result

    @property
    def id(self):
        return self.get_meta('id')

    @property
    def contents(self):
        return self._contents

    @property
    def title(self):
        return self.get_meta('title')

    # sets contents to be a dict mapping file names to contents
    # force_refresh = True forces to re-fetch the contents even if we have
    # already done so
    def fetch_contents(self, client, **kwargs):
        Log.debug(u'Fetching contents for doc id {}'.format(self.id))
        if self._contents is None \
            or 'force_refresh' in kwargs \
                and kwargs['force_refresh']:
            self._contents = dict()
            for url in self._get_download_urls():
                file_name, content = self._download_from_url(client, url)
                self._contents[file_name] = content

    def del_contents(self):
        self._contents = None

    def get_meta(self, key, default=None):
        if key in self._meta:
            return self._meta[key]
        return default

    def _get_download_urls(self):
        if 'downloadUrl' in self._meta:
            return [self._meta['downloadUrl']]
        elif 'exportLinks' in self._meta:
            return self._meta['exportLinks'].values()
        else:
            Log.verbose(u'No download URL for document id {}'.format(self.id))
            return []

    @Utils.multiple_tries_decorator(ExpiredTokenException)
    def _download_from_url(self, client, url):
        try:
            headers, content = client.request(url)
            self._check_download_integrity(headers, content)
            return self._get_file_name(headers), content
        except KeyError:
            # token expired
            raise ExpiredTokenException()

    def _check_download_integrity(self, headers, content):
        Log.debug(u'Checking download integrity for doc id {}'.format(self.id))
        success, message = True, None
        # content length
        content_length = int(headers.get('content-length', 0))
        if content_length and content_length != StringIO(content).len:
            success = False
            message = u'expected length {} VS actual length {}'.format(
                content_length, len(content)
            )
        # md5 check
        expected_sum = self.get_meta('md5Checksum')
        if success and expected_sum:
            md5_object = md5.new()
            md5_object.update(content)
            actual_sum = md5_object.hexdigest()
            if expected_sum != actual_sum:
                success = False
                message = u'expected md5 sum {} VS actual {}'.format(
                    expected_sum, actual_sum
                )
        if not success:
            err_message = u'Failed to download document id {}: {}'.format(
                self.id, message
            )
            Log.verbose(err_message)
            raise Exception(err_message)

    def _get_file_name(self, headers):
        # get from the headers
        content_disposition = headers['content-disposition']
        name_matches = Document._name_from_header_regex.findall(
            content_disposition
        )
        if not name_matches:
            raise Exception(
                u'Unexpected "content_disposition" header: {}'.format(
                    content_disposition
                )
            )
        raw_name = name_matches[0]
        result = u'{}_{}'.format(self.title, self.id)
        # insert the doc id in the name (just before the extension)
        # to make sure it's unique
        extension_matches = Document._split_extension_regex.findall(raw_name)
        if extension_matches:
            extension = extension_matches[0]
            result += u'.{}'.format(extension)
        return result
