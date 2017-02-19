from setuptools import setup

install_requires = [
    'requests >= 2.13',
    'rfc6266 >= 0.0.4',
    'pathvalidate >= 0.14',
]

tests_require = [
    'pytest >= 3.0',
    'pytest-flake8 >= 0.8',
    'responses >= 0.5',
]

setup_requires = [
    'pytest-runner',
]

setup(
    name='image-downloader',
    version='1.0',
    url='https://www.github.com/skoslowski/image-downloader',
    license='GPLv3',
    author='Sebastian Koslowski',
    author_email='sebastian.koslowski@gmail.com',
    description='Download all images listed in a file of URLs',

    install_requires=install_requires,
    tests_require=tests_require,
    setup_requires=setup_requires,

    py_modules=['image_downloader'],
    scripts=['image_downloader.py'],
)
