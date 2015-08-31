#!/usr/bin/env python3

from setuptools import setup

setup(
    name='autotex',
    version='0.1',
    url='https://github.com/crepererum/hyperion',
    author='Marco Neumann',
    author_email='marco@crepererum.net',
    keywords='LaTeX',
    license='LPPL',
    platforms='linux',
    zip_safe=True,
    packages=[
        'autotex',
    ],
    entry_points={
        'console_scripts': [
            'autotex = autotex.__main__:run'
        ]
    },
    install_requires=[
        'msgpack-python>=0.4.2',
        'pyinotify>=0.9.4',
        'PyYAML>=3.11',
    ],
    extras_require={
        'dev': [
            'flake8>=2.2.3',
            'pylint>=1.3.1',
        ],
    },
)
