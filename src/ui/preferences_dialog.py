#!/usr/bin/env python3
"""
Preferences Dialog
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw
import logging

logger = logging.getLogger(__name__)


class PreferencesDialog(Adw.PreferencesWindow):
    """Application settings dialog"""

    def __init__(self, parent, app_config, **kwargs):
        super().__init__(**kwargs)

        self.app_config = app_config
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_search_enabled(False)

        # Create settings page
        page = Adw.PreferencesPage()
        page.set_title("Settings")
        page.set_icon_name("preferences-system-symbolic")

        # RDP Settings Group
        rdp_group = Adw.PreferencesGroup()
        rdp_group.set_title("RDP Server")
        rdp_group.set_description("xrdp server settings")

        # Default port field
        self.port_row = Adw.SpinRow()
        self.port_row.set_title("Default Port")
        self.port_row.set_subtitle("Port used by all RDP users")

        # Configure adjustment (min, max, step)
        adjustment = Gtk.Adjustment()
        adjustment.set_lower(1)
        adjustment.set_upper(65535)
        adjustment.set_step_increment(1)
        adjustment.set_page_increment(10)
        adjustment.set_value(self.app_config.get_default_rdp_port())

        self.port_row.set_adjustment(adjustment)
        self.port_row.set_digits(0) # No decimal places

        # Connect turn signal
        self.port_row.connect('changed', self.on_port_changed)

        rdp_group.add(self.port_row)

        # Add group to page
        page.add(rdp_group)

        # Add page to window
        self.add(page)

    def on_port_changed(self, spin_row):
        """Callback when port is changed"""
        new_port = int(spin_row.get_value())

        # Save configuration
        success = self.app_config.set_default_rdp_port(new_port)

        if success:
            logger.info(f"Default port changed to: {new_port}")
        else:
            logger.error(f"Error changing port to: {new_port}")
