# -*- coding: utf-8 -*-

import md5
import re
from StringIO import StringIO
import mimetypes
import dateutil.parser
import time
import os
import tempfile

from oauth2client.client import AccessTokenRefreshError

import client as client_module
from utils import *
from apiclient.errors import HttpError
from configuration import Configuration


class User:

    def __init__(self, login, client, need_folders=True):
        # check that we have only the login, not the full email address
        if '@' in login:
            login = login.partition('@')[0]
        self._login = login
        self._client = client
        self._documents = None
        self._folders = UserFolders(self) if need_folders else None
        self._black_listed_ids = []

    def __repr__(self):
        return self._login

    @property
    def login(self):
        return self._login

    @property
    def folders(self):
        return self._folders

    @property
    def document_generator(self):
        # let's filter folders out
        return client_module.UserDocumentsGenerator(
            self, Document.get_folder_query()
        )

    # just the doc ids
    @property
    def document_ids(self):
        return [doc.id for doc in self.document_generator]

    @property
    def drive_service(self):
        client = self._client
        client.authorize(self)
        return client.drive_service

    def save_documents(self, backend, owned_only):
        Log.verbose(u'Processing docs for {}'.format(self.login))
        doc_generator = self.document_generator
        for document in doc_generator:
            if not backend.need_to_fetch_contents(self, document)\
                    or (owned_only and not document.is_owned):
                # mark as done, and get to the next one
                Log.verbose(
                    u'Not necessary to fetch doc id {}'.format(document.id)
                )
                doc_generator.add_processed_id(document.id)
                continue

            Log.verbose(u'Processing {}\'s doc "{}" (id: {})'.format(
                self.login, document.title, document.id
            ))
            try:
                document.fetch_contents(self._client)
                self._save_single_document(backend, document)
            except client_module.ExpiredTokenException as ex:
                if document.id in self._black_listed_ids:
                    # we already got a 403 on that one!
                    explanation = 'Two 403 errors on a row on document id {}'\
                        .format(document.id)
                    ex.brive_explanation = explanation
                    raise
                # otherwise try again
                Log.verbose(
                    '403 response, sleeping one minute and re-trying...'
                )
                time.sleep(60)
                # the re-auth is handled by the the list request
                doc_generator.reset_to_current_page()
                self._black_listed_ids.append(document.id)
                continue
            except Exception as ex:
                explanation = \
                    'Unexpected error when processing ' \
                    + '{}\'s documents '.format(self.login) \
                    + u'(doc id: {})'.format(document.id)
                ex.brive_explanation = explanation
                raise
            # mark as done
            doc_generator.add_processed_id(document.id)
        # let's save some memory
        self._cleanup()
        backend.close_user(self)

    def retrieve_single_document(self, backend, doc_id):
        try:
            document = self.retrieve_single_document_meta(doc_id)
        except Exception as e:
            explanation = 'Error while retrieving single document id ' \
                + u'{} for user {}, '.format(doc_id, self.login) \
                + 'it\'s liklely this user isn\'t allowed to see that doc'
            e.brive_explanation = explanation
            raise
        document.fetch_contents(self._client)
        self._save_single_document(backend, document)

    # NOTE: Google's API doesn't like to get a lot of such calls,
    # so use defensively...
    @Utils.multiple_tries_decorator(None)
    def retrieve_single_document_meta(self, doc_id):
        try:
            meta = self.drive_service.files().get(fileId=doc_id).execute()
            return Document(meta, self.folders)
        except AccessTokenRefreshError:
            # most likely 403
            raise client_module.ExpiredTokenException

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

    def _cleanup(self):
        del self._documents
        del self._folders
        del self._black_listed_ids


# keeps tracks of the user's folders, and caches the paths to them
class UserFolders:

    def __init__(self, user):
        self._user = user
        self._initialized = False

    def get_path(self, folder_id):
        if folder_id is None:
            # the root has ID None by convention
            return ''
        self._do_init()
        folder = self._folders[folder_id]
        parent_path = self.get_path(folder.parent_id)
        parent_path += os.sep if parent_path else ''
        return parent_path + folder.title

    def _do_init(self):
        if self._initialized:
            return
        self._initialized = True
        Log.debug(u'Initializing folders for user {}'.format(self._user.login))
        # dict that maps a folder id to its object
        self._folders = self._build_folders()

    def _build_folders(self):
        folder_generator = client_module.UserDocumentsGenerator(
            self._user, Document.get_folder_query(False), Folder
        )
        return {folder.id: folder for folder in folder_generator}


class DocumentContent(object):

    def __init__(self, client, url, document):
        self._client = client
        self._url = url
        self._document = document
        headers, self._content = self._make_request()
        self.file_name = self._get_file_name(headers)
        self.size = None

    _CHUNK_SIZE = 1048576  # 1 Mb

    # returns a file-like object
    # if size_requested is set to True, then the self.size attribute
    # will be accurate after this returns
    def get_file_object(self, size_requested=False):
        if self._client.streaming:
            _, self._content = self._make_request()
            if not size_requested or self.size is not None:
                return self._content
            # we need to copy the whole thing to the disk, and then return it
            Log.debug(u'Copying to temp file {}'.format(self.file_name))
            result = tempfile.TemporaryFile()
            self.write_to_file(result, True)
            self.size = os.fstat(result.fileno()).st_size
            # let's rewind the file before returning it
            result.seek(0)
        else:
            result = StringIO(self._content)
            if size_requested:
                self.size = result.len
        return result

    def write_to_file(self, f, content_up_to_date=False):
        if self._client.streaming:
            if not content_up_to_date:
                _, self._content = self._make_request()
            for blck in iter(lambda: self._content.read(self._CHUNK_SIZE), ''):
                f.write(blck)
        else:
            f.write(self._content)
        f.flush()

    @Utils.multiple_tries_decorator(client_module.ExpiredTokenException)
    def _make_request(self):
        return self._client.request(
            self._url, brive_expected_error_status=403,
            brive_streaming=True
        )

    _split_extension_regex = re.compile(r'\.([^.]+)$')
    _name_from_header_regex = re.compile(
        r'^attachment;\s*filename(?:="|\*=[A-Za-z0-9-]+\'\')([^"]+)(?:"|$)'
    )

    def _get_file_name(self, headers):
        # get from the headers
        content_disposition = headers['content-disposition']
        name_matches = self._name_from_header_regex.findall(
            content_disposition
        )
        if not name_matches:
            raise Exception(
                u'Unexpected "content_disposition" header: {}'.format(
                    content_disposition
                )
            )
        raw_name = name_matches[0]
        # insert the doc id in the name (just before the extension)
        # to make sure it's unique
        result = u'{}_{}'.format(self._document.title, self._document.id)
        extension_matches = self._split_extension_regex.findall(raw_name)
        if extension_matches:
            extension = extension_matches[0]
            result += u'.{}'.format(extension)
        return result


class Document(object):

    _extension_from_url_regex = re.compile(r'exportFormat=([^&]+)$')

    _folder_mime_type = r'application/vnd.google-apps.folder'

    _exclusive_formats = dict()

    def __init__(self, meta, user_folders):
        self._meta = meta
        self._user_folders = user_folders
        self._contents = None

    def __repr__(self):
        return u'Meta: {}'.format(self._meta)

    @property
    def id(self):
        return self.get_meta('id')

    @property
    def contents(self):
        return self._contents

    @property
    def title(self):
        # forbid os.sep in the name, and replace it with '_',
        # to prevent bugs when saving
        return self.get_meta('title').replace(os.sep, '_')

    @property
    def is_owned(self):
        try:
            return self.get_meta('userPermission', {})['role'] == 'owner'
        except KeyError:
            return False

    @property
    def is_folder(self):
        return self.get_meta('mimeType') == Document._folder_mime_type

    @property
    def path(self):
        result = self._user_folders.get_path(self.parent_id)
        result += os.sep if result else ''
        return result

    @property
    def parent_id(self):
        try:
            parent = self.get_meta('parents')[0]
            if parent['isRoot']:
                return None
            return parent['id']
        except IndexError:
            return None

    @property
    def modified_timestamp(self):
        try:
            datetime_object = dateutil.parser.parse(
                self.get_meta('modifiedDate')
            )
            return int(time.mktime(datetime_object.timetuple()))
        except Exception:
            # not a big deal if that fails from time to time
            return 0

    # sets contents to be a dict mapping file names to contents
    # force_refresh = True forces to re-fetch the contents even if we have
    # already done so
    def fetch_contents(self, client, force_refresh=False):
        if self._contents is None or force_refresh:
            self._contents = []
            self._do_fetch_contents(client)

    # returns the query string to use to call Google's API
    @staticmethod
    def get_folder_query(exclude=True):
        return "%smimeType = '%s'" % (
            'not ' if exclude else '', Document._folder_mime_type
        )

    def _do_fetch_contents(self, client, second_try=False, banned_urls=list()):
        debug_msg = u'Fetching contents for doc id {}'.format(self.id)
        if second_try:
            debug_msg += ', this time ignoring extension preferences'
        Log.debug(debug_msg)
        urls = self._get_download_urls(second_try, banned_urls)
        for url in urls:
            try:
                Log.verbose(u'Starting download from {}'.format(url))
                self._contents.append(self._download_from_url(client, url))
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
                ext_matches = Document._extension_from_url_regex.findall(url)
                if not ext_matches:
                    # shouldn't happen as far as I can tell
                    Log.error(u'No extension found in url: {} '.format(url)
                              + u'for document id {}'.format(self.id))
                    continue
                extension = '.' + ext_matches[0]
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

    def _download_from_url(self, client, url):
        try:
            return DocumentContent(
                client, url, self
            )
        except (KeyError, client_module.ExpectedFailedRequestException):
            # token expired, or an "User Rate Limit Exceeded" error,
            raise ExpiredTokenException()


# it's only a folder, no need to keep all the meta data
# (just parent_id and title)
class Folder(Document):

    def __init__(self, meta, user_folders):
        super(Folder, self).__init__(meta, user_folders)
        new_meta = {key: meta[key] for key in ('id', 'parents', 'title')}
        del self._meta
        self._meta = new_meta
