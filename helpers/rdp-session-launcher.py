#!/usr/bin/env python3
"""
RDP Session Launcher
Fullscreen modern white interface presented upon RDP login to select connection sources.
"""

import sys
import os
import json
import logging
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rdp-session-launcher")


class SessionLauncherApp(Adw.Application):
    def __init__(self, profiles, **kwargs):
        super().__init__(application_id="org.rdp.SessionLauncher", **kwargs)
        self.profiles = profiles
        self.selected_profile = None

    def do_activate(self):
        win = Adw.ApplicationWindow(application=self, title="RDP Session Launcher")
        win.set_decorated(False)
        win.maximize()
        win.fullscreen()

        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                mon = monitors.get_item(0)
                geom = mon.get_geometry()
                win.set_default_size(geom.width, geom.height)

        # Custom CSS for bright, modern light/white theme
        css_provider = Gtk.CssProvider()
        css_code = """
        window.launcher-window {
            background-color: #f3f4f6;
        }
        .launcher-card {
            background-color: #ffffff;
            border-radius: 24px;
            border: 1px solid #e5e7eb;
            padding: 36px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.08);
        }
        .launcher-title {
            font-size: 24px;
            font-weight: 800;
            color: #111827;
            margin-top: 8px;
        }
        .launcher-subtitle {
            font-size: 14px;
            color: #6b7280;
            margin-top: 4px;
        }
        """
        css_provider.load_from_data(css_code.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        win.add_css_class("launcher-window")

        # Force light theme for this window
        style_manager = Adw.StyleManager.get_for_display(Gdk.Display.get_default())
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)

        # Root layout centering the card modal in fullscreen
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_halign(Gtk.Align.CENTER)

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        card_box.add_css_class("launcher-card")
        card_box.set_size_request(520, -1)

        # Header icon & title
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        icon.set_pixel_size(56)
        header_box.append(icon)

        title_label = Gtk.Label(label="Select Connection Source")
        title_label.add_css_class("launcher-title")

        subtitle_label = Gtk.Label(label="Choose the application or environment to launch for this session:")
        subtitle_label.add_css_class("launcher-subtitle")
        subtitle_label.set_wrap(True)
        subtitle_label.set_justify(Gtk.Justification.CENTER)

        header_box.append(title_label)
        header_box.append(subtitle_label)
        card_box.append(header_box)

        # List of profiles
        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        for profile in self.profiles:
            row = Adw.ActionRow()
            row.set_title(profile.get("name", "RDP Connection"))

            p_type = profile.get("profile_type", "desktop")
            if p_type == "desktop":
                de = str(profile.get("desktop_env", "xfce")).upper()
                row.set_subtitle(f"Full Desktop Environment ({de})")
                row.set_icon_name("computer-symbolic")
            elif p_type == "remoteapp":
                cmd = profile.get("app_command", "")
                row.set_subtitle(f"Linux Application: {cmd}")
                row.set_icon_name("application-x-executable-symbolic")
            elif p_type == "winege-remoteapp":
                cmd = Path(profile.get("app_command", "")).name
                row.set_subtitle(f"Windows Application (WineGE): {cmd}")
                row.set_icon_name("application-x-executable-symbolic")

            btn = Gtk.Button(label="Launch")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)

            def on_click(b, p=profile):
                self.selected_profile = p
                print(json.dumps(p))
                win.close()
                self.quit()

            btn.connect("clicked", on_click)
            row.add_suffix(btn)
            row.set_activatable_widget(btn)
            list_box.append(row)

        card_box.append(list_box)
        center_box.append(card_box)
        win.set_content(center_box)
        win.present()


def main():
    home_dir = Path(os.environ.get("HOME", "/root"))
    profiles_file = home_dir / ".rdp_profiles.json"

    if not profiles_file.exists():
        logger.error(f"Profiles file not found: {profiles_file}")
        sys.exit(1)

    try:
        with open(profiles_file, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                profiles = data.get("profiles", [])
            else:
                profiles = data
    except Exception as e:
        logger.error(f"Failed to read profiles: {e}")
        sys.exit(1)

    if not isinstance(profiles, list) or not profiles:
        logger.error("No valid profiles found in profiles.json")
        sys.exit(1)

    # Check command line arguments if profile specified
    if len(sys.argv) > 1 and sys.argv[1]:
        req_id = sys.argv[1]
        for p in profiles:
            if p.get("profile_id") == req_id or p.get("name") == req_id:
                print(json.dumps(p))
                sys.exit(0)

    # If single profile, auto select
    if len(profiles) == 1:
        print(json.dumps(profiles[0]))
        sys.exit(0)

    app = SessionLauncherApp(profiles)
    app.run(None)


if __name__ == "__main__":
    main()
