# Image Downloader

Reads a list of image URLs from a file and downloads them using thread-based concurrency.

Example usage (see command line help page for details):
```sh
image_downloader.py links.txt --out-dir=downloads
```
Supports both Python 3 and Python 2.7. Dependencies (PyPI packages):
* requests
* pathvalidate
* rfc6266
* futures (Python 2 only)

To run tests use 
```sh
python setup.py test
```
or run `pytest` after installing the dependencies with `pip install -r requirements-dev.txt`
