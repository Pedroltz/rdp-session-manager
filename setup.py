#!/usr/bin/env python3
"""
RDP Session Manager - Setup Script
Gerenciador de sessões RDP com interface GTK4 para GNOME
"""

from setuptools import setup, find_packages

setup(
    name='rdp-session-manager',
    version='0.1.0',
    description='Gerenciador de sessões RDP com interface GTK4',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/rdp-session-manager',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'PyGObject>=3.42.0',
        'pycairo>=1.20.0',
    ],
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            'rdp-session-manager=main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: System :: Systems Administration',
    ],
)
