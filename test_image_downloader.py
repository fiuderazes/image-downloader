"""Tests for image_downloader.py"""
import io

import pytest
import requests
import responses

import image_downloader


@pytest.mark.parametrize('resource_name,content_type,expected_filename', [
    ('foobar.jpg', 'image/jpg', 'foobar.jpg'),
    ('foobar.JPEG', 'image/jpeg', 'foobar.JPEG'),
    ('foobar.jpg', 'image/jpeg', 'foobar.jpg'),
    ('foobar.jpeg', 'image/jpg', 'foobar.jpeg'),
    ('foobar.jpg', 'image/bmp', 'foobar.jpg.bmp'),
])
@responses.activate
def test_download_image(resource_name, content_type, expected_filename, tmpdir):
    url = 'http://abc.de/bla/' + resource_name
    responses.add(responses.GET, url, content_type=content_type, stream=io.StringIO(u''))
    filename = image_downloader.download_image(url, str(tmpdir))
    assert filename == expected_filename
    assert tmpdir.join(filename).exists()


@responses.activate
def test_invalid_url(tmpdir):
    with pytest.raises(requests.exceptions.ConnectionError):
        image_downloader.download_image('http://nonexistent.de/image.png', str(tmpdir))


@responses.activate
def test_fail404(tmpdir):
    url = 'http://abc.de/bla/foobar.jpg'
    responses.add(responses.GET, url, status=404, content_type='text/plain')
    with pytest.raises(requests.exceptions.HTTPError):
        image_downloader.download_image(url, str(tmpdir))


@responses.activate
def test_wrong_content_type(tmpdir):
    url = 'http://abc.de/bla/foobar.jpg'
    responses.add(responses.GET, url, body='', content_type='text/plain')
    with pytest.raises(ValueError) as excinfo:
        image_downloader.download_image(url, str(tmpdir))
    excinfo.match('Invalid image type')


def test_rename_if_exists(tmpdir):
    file_path = tmpdir.join('test.jpg')
    file_path_1 = tmpdir.join('test_1.jpg')
    file_path_2 = tmpdir.join('test_2.jpg')

    assert file_path == image_downloader.rename_if_exists(str(file_path))
    file_path.open('w').close()
    assert file_path_1 == image_downloader.rename_if_exists(str(file_path))
    file_path_1.open('w').close()
    assert file_path_2 == image_downloader.rename_if_exists(str(file_path))


def test_download_manager(monkeypatch, tmpdir):
    """test the download manager with a mocked image downloader"""
    def download_image_mock(url, out_dir):
        if 'raise' in url:
            raise ValueError('failed')
        return ''
    monkeypatch.setattr(image_downloader, 'download_image', download_image_mock)

    url_list = u"""
        success
        success

        raise
        raise
        success
    """
    stats = image_downloader.download_manager(io.StringIO(url_list), str(tmpdir), max_workers=2)
    assert stats.failed == url_list.count('raise')
    assert stats.success == url_list.count('success')
    assert stats.total == 5
