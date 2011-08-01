# -*- coding: utf-8 -*-
"""setup -- setuptools setup file for Python Game Tools.

$Author: Raymond Chandler III $
"""

__author__ = "Raymond Chandler III"
__author_email__ = "raymondchandleriii@gmail.com"
__version__ = "0.0.1"
__date__ = "2011 07 31"

try:
    import setuptools
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()

from setuptools import setup, find_packages

f = open('README','rU')
long_description = f.read()
f.close()

setup(
    name = "python-game-tools",
    version = __version__,
    author = "Raymond Chandler III",
    license="BSD",
    description = "A distribution of pyglet, cocos2d, kytten, and pyglet",
    long_description=long_description,
    url = "https://github.com/kitanata/Python-Game-Tools",
    download_url = "https://github.com/kitanata/Python-Game-Tools/tarball/master",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        ("Topic :: Software Development :: Libraries :: Python Modules"),
        ("Topic :: Games/Entertainment"),
        ],

    install_requires=['pyglet>=1.1.4', 
			'cocos2d>=0.4.0',
			 'kytten>=6.0.0',
			 'cocograph>=0.1.0'],
    dependency_links=['http://code.google.com/p/pyglet/downloads/list',
			'http://code.google.com/p/los-cocos/downloads/list',
			'https://github.com/kitanata/Kytten/tarball/master',
			'https://github.com/kitanata/cocograph/tarball/master'],

    include_package_data = True,
    zip_safe = False,    
)
