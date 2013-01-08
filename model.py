# -*- coding: utf-8 -*-

import md5
import re
from StringIO import StringIO
import mimetypes
import dateutil.parser
import time

import client as client_module
from utils import *
from apiclient.errors import HttpError
from configuration import Configuration


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

    # just the doc ids
    @property
    def document_ids(self):
        return [doc.id for doc in self.documents]

    @property
    def drive_service(self):
        client = self._client
        client.authorize(self)
        return client.drive_service

    def save_documents(self, backend):
        Log.verbose(u'Processing docs for {}'.format(self.login))
        doc_generator = client_module.UserDocumentsGenerator(self)
        for document in doc_generator:
            if not backend.need_to_fetch_contents(self, document):
                # mark as done, and get to the next one
                Log.verbose(
                    u'Not necessary to fetch doc id '.format(document.id)
                )
                doc_generator.add_processed_id(document.id)
                continue

            Log.verbose(u'Processing {}\'s doc "{}" (id: {})'.format(
                self.login, document.title, document.id
            ))
            try:
                document.fetch_contents(self._client)
            except client_module.ExpiredTokenException:
                # the re-auth is handled by the the list request
                doc_generator.reset_to_current_page()
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
            doc_generator.add_processed_id(document.id)

    def retrieve_single_document(self, backend, doc_id):
        try:
            meta = self._do_retrieve_single_document(doc_id)
            document = Document(meta)
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
    _extension_from_url = re.compile(r'exportFormat=([^&]+)$')

    _exclusive_formats = dict()

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

    @property
    def modified_timestamp(self):
        try:
            datetime_object = dateutil.parser.parse(self.get_meta('modifiedDate'))
            return int(time.mktime(datetime_object.timetuple()))
        except Exception:
            # not a big deal if that fails from time to time
            return 0

    # sets contents to be a dict mapping file names to contents
    # force_refresh = True forces to re-fetch the contents even if we have
    # already done so
    def fetch_contents(self, client, force_refresh=False):
        if self._contents is None or force_refresh:
            self._do_fetch_contents(client)

    def _do_fetch_contents(self, client, second_try=False, banned_urls=list()):
        debug_msg = u'Fetching contents for doc id {}'.format(self.id)
        if second_try:
            debug_msg += ', this time ignoring extension preferences'
        Log.debug(debug_msg)
        self._contents = dict()
        urls = self._get_download_urls(second_try, banned_urls)
        for url in urls:
            try:
                Log.verbose(u'Starting download from {}'.format(url))
                file_name, content = self._download_from_url(client, url)
                self._contents[file_name] = content
            except client_module.FailedRequestException:
                Log.error(u'Download from {} for document {} failed'
                          .format(url, self.id))
                banned_urls.append(url)
        if not self._contents:
            if second_try:
                Log.error('Couldn\'t retrieve any version of document id '
                          + u'{} (title: {})'.format(self.id, self.title))
            else:
                # we've failed to retrieve any contents, we try again,
                # this time ignoring format preferences
                self._do_fetch_contents(client, True, banned_urls)

    def del_contents(self):
        del self._contents
        self._contents = None

    def get_meta(self, key, default=None):
        if key in self._meta:
            return self._meta[key]
        return default

    def _get_download_urls(self, ignore_preferred=False, banned_urls=list()):
        result = []
        if 'downloadUrl' in self._meta:
            # filter if exclusive formats are set
            if Document._is_an_exclusive_format(self.get_meta('mimeType')):
                result = [self._meta['downloadUrl']]
        elif 'exportLinks' in self._meta:
            # no direct download link
            urls = self._meta['exportLinks'].values()
            url_to_ext = dict()
            # filter exclusive and preferred formats
            exclusive = Configuration.get('formats_exclusive')
            preferred = Configuration.get('formats_preferred')
            one_preferred_found = False
            for url in urls:
                # get the extension from the url
                extension_matches = Document._extension_from_url.findall(url)
                if not extension_matches:
                    # shouldn't happen as far as I can tell
                    Log.error(u'No extension found in url: {} '.format(url)
                              + u'for document id {}'.format(self.id))
                    continue
                extension = '.' + extension_matches[0]
                Log.debug(
                    u'Found extension {} for document id {}'.format(
                        extension, self.id
                    )
                )
                if exclusive and not extension in exclusive:
                    Log.debug(u'Ignoring extension {} not '.format(extension)
                              + u'not in exclusive: {}'.format(exclusive))
                    continue
                if not ignore_preferred and extension in preferred:
                    one_preferred_found = True
                url_to_ext[url] = extension
            if one_preferred_found:
                result = [url for url in url_to_ext.keys()
                          if url_to_ext[url] in preferred]
            else:
                result = url_to_ext.keys()
        # filter banned URLs
        if banned_urls:
            result = [url for url in result if url not in banned_urls]
        # and finally, return if anything is left!
        if not result:
            Log.verbose(
                u'No suitable download URL for document id {}'.format(self.id)
            )
        return result

    @staticmethod
    def _is_an_exclusive_format(mimeType):
        exclusive = Configuration.get('formats_exclusive')
        if not exclusive:
            return True
        if format not in Document._exclusive_formats:
            possible_exts = set(
                mimetypes.guess_all_extensions(mimeType, strict=False)
            )
            result = bool(possible_exts.intersection(exclusive))
            Document._exclusive_formats[format] = result
        return Document._exclusive_formats[format]

    @Utils.multiple_tries_decorator(client_module.ExpiredTokenException)
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
