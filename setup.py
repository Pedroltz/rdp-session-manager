#!/usr/bin/env python3
"""
RDP Session Manager - Setup Script
Gerenciador de sessões RDP com interface GTK4 para GNOME
"""

from setuptools import setup, find_packages
from pathlib import Path
import glob
import re

VERSION = re.search(r'__version__\s*=\s*["\']([^"\']+)', Path('src/version.py').read_text()).group(1)

# Get all helper scripts
helper_scripts = glob.glob('helpers/*.sh')

setup(
    name='rdp-session-manager',
    version=VERSION,
    description='Gerenciador de sessões RDP com interface GTK4',
    author='Pedroltz',
    author_email='your.email@example.com',
    url='https://github.com/Pedroltz/rdp-session-manager',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    data_files=[
        # Install helper scripts to /usr/share/rdp-session-manager/helpers
        ('share/rdp-session-manager/helpers', helper_scripts),
    ],
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
