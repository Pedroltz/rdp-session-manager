#!/usr/bin/env python3
"""
RDP Session Manager - Entry point
"""

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio
from application import RDPSessionManagerApp
from utils.logger import setup_logger

def main():
    """Main entry point"""
    # Setup logging
    logger = setup_logger('rdp-session-manager')
    logger.info("Starting RDP Session Manager")

    # Create and run application
    app = RDPSessionManagerApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
