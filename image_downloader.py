#!/usr/bin/env python3
"""
This script reads a list of image URLs from a file and downloads them.

Downloaded images are saved to the specified folder.
Other types of files are not downloaded!
Thread-based concurrency is used to speed-up the process
"""

import argparse
import collections
import logging
import os
import shutil
import sys
import threading

from concurrent import futures
from os import path

import pathvalidate
import requests
import rfc6266

__version__ = '1.0'

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

DownloadStats = collections.namedtuple('DownloadStats', 'success failed total')


def download_manager(url_file, out_dir='.', max_workers=None):
    """Concurrently download images listed in url_file to out_dir

    url_file can a filename or a file-like object
    max_workers limits the number of concurrent downloads
    """
    if not hasattr(url_file, 'read'):
        url_file = open(url_file, 'r')
    if not path.isdir(out_dir):
        raise ValueError('Invalid output directory %r', out_dir)

    # python2 back-port of concurrent.futures has no default max_workers
    if sys.version_info.major < 3 and max_workers is None:
        max_workers = 10

    error_count = 0
    with url_file, futures.ThreadPoolExecutor(max_workers) as executor:
        # read and queue downloads
        urls = (line.strip() for line in url_file if line.strip())
        fs = [executor.submit(download_image, url, out_dir) for url in urls]

        # log and count errors
        for f in futures.as_completed(fs):
            error = f.exception()
            if error:
                error_count += 1
                logger.error(error)

    return DownloadStats(success=len(fs) - error_count, failed=error_count, total=len(fs))


def download_image(url, out_dir):
    """Download a single image from url and save it to out_dir"""
    logger.debug('Requesting %r', url)
    response = get_session().get(url, stream=True)
    response.raise_for_status()

    # check mime type
    content_type = response.headers.get('content-type', '').split(';', 1)[0]
    media_type, _, subtype = content_type.partition('/')
    if media_type != 'image' or not subtype:
        response.close()
        raise ValueError('Invalid image type {!r} from {!r}'.format(content_type, url))

    # read filename from content-disposition header
    filename = get_filename(response, expected_extension=subtype)
    filename = pathvalidate.sanitize_filename(filename, replacement_text='_')
    file_path = rename_if_exists(file_path=path.join(out_dir, filename))

    # save to out_dir
    with open(file_path, 'wb') as downloaded_file:
        shutil.copyfileobj(response.raw, downloaded_file)

    logger.debug('Saved %r', path.basename(file_path))
    return filename


def get_filename(response, expected_extension):
    """Get filename from content-disposition header"""
    try:
        content_disposition = rfc6266.parse_requests_response(response)
    except Exception as error:  # lets not depend on the dependencies of rfc6266
        logger.warning('Failed to parse content_disposition header from %r, error: %r',
                       response.url, error)
        # fall back on guessing the filename from the URL
        basename = requests.utils.unquote_unreserved(response.url).rsplit('/', 1)[-1]
        return (basename or 'file') + '.' + expected_extension

    extension = content_disposition.filename_unsafe.rsplit('.', 1)[-1]
    # allow for some common file extension variations
    safe_aliases = (extension.lower(),
                    extension.lower().replace('jpeg', 'jpg'),
                    extension.lower().replace('jpg', 'jpeg'))
    if expected_extension in safe_aliases:
        expected_extension = extension

    return content_disposition.filename_sanitized(expected_extension)


def rename_if_exists(file_path):
    """Appends a number (max 10000) to the filename if it already exists"""
    if not path.exists(file_path):
        return file_path

    dirname = path.dirname(file_path)
    basename, _, ext = path.basename(file_path).rpartition('.')
    for i in range(1, 10000):
        file_path = path.join(dirname, '{}_{}.{}'.format(basename, i, ext))
        if not path.exists(file_path):
            break
    else:
        logger.warning('Failed to rename %r', file_path)

    return file_path


def get_session():
    """Get a thread-local session object.

    Session instances are not thread-safe.
    See https://github.com/kennethreitz/requests/issues/2766
    """
    local = threading.local()
    try:
        session = local.session
    except AttributeError:
        session = local.session = requests.Session()

    return session


def main(args=None):
    """Parse command line arguments, setup logging, call download manager"""
    parser = argparse.ArgumentParser(
        description='Reads image URLs from an input file and downloads them. '
                    'Version ' + __version__
    )
    parser.add_argument(metavar='FILE', type=argparse.FileType('r'), dest='filename',
                        help="text file to read URLS from. One per line.")
    parser.add_argument('-o', '--out-dir', metavar='DIR', dest='out_dir', default='.',
                        help='download folder (default: %(default)s')
    parser.add_argument('-n', '--workers', type=int, metavar='N', dest='max_workers',
                        default=None, help='Maximum number of concurrent downloads')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='enable debug logging')
    options = parser.parse_args(args)

    logger.level = logging.DEBUG if options.verbose else logging.INFO

    if not path.exists(options.out_dir):
        logger.info('Creating %r', path.normpath(options.out_dir))
        try:
            os.makedirs(options.out_dir)
        except OSError:
            logger.error('Invalid output directory %r', path.normpath(options.out_dir))
            return -1

    stats = download_manager(options.filename, options.out_dir, options.max_workers)
    logger.info('Downloaded %d files, %d failed (%s entries in file)', *stats)


if __name__ == '__main__':
    # fix default logging in rfc6266 package
    rfc6266.LOGGER.removeHandler(logging.NullHandler)  # yes, the class
    rfc6266.LOGGER.addHandler(logging.NullHandler())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('{levelname:7} {message}', style='{'))
    logger.addHandler(handler)

    sys.exit(main())
