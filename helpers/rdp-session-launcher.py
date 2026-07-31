#!/usr/bin/env python3
"""
RDP Session Launcher
Interface GTK4/Libadwaita exibida ao conectar via RDP quando o usuário possui múltiplas fontes de conexão.
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
        win = Adw.ApplicationWindow(application=self, title="Seleção de Sessão RDP")
        win.set_default_size(520, 420)
        win.set_resizable(False)

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)

        # Header icon & title
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.set_halign(Gtk.Align.CENTER)

        title_label = Gtk.Label(label="Escolha a Fonte de Conexão")
        title_label.add_css_class("title-1")

        subtitle_label = Gtk.Label(label="Selecione o ambiente ou aplicativo que deseja utilizar nesta sessão:")
        subtitle_label.add_css_class("dim-label")

        header_box.append(title_label)
        header_box.append(subtitle_label)
        main_box.append(header_box)

        # Clamp container
        clamp = Adw.Clamp(maximum_size=460)
        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        for profile in self.profiles:
            row = Adw.ActionRow()
            row.set_title(profile.get("name", "Conexão RDP"))
            
            p_type = profile.get("profile_type", "desktop")
            if p_type == "desktop":
                de = str(profile.get("desktop_env", "xfce")).upper()
                row.set_subtitle(f"Área de Trabalho Completa ({de})")
                row.set_icon_name("computer-symbolic")
            elif p_type == "remoteapp":
                cmd = profile.get("app_command", "")
                row.set_subtitle(f"Aplicativo Linux: {cmd}")
                row.set_icon_name("application-x-executable-symbolic")
            elif p_type == "winege-remoteapp":
                cmd = Path(profile.get("app_command", "")).name
                row.set_subtitle(f"Aplicativo Windows (WineGE): {cmd}")
                row.set_icon_name("wine-symbolic" if Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).has_icon("wine-symbolic") else "application-x-executable-symbolic")

            btn = Gtk.Button(label="Iniciar")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)
            
            # Store profile in closure
            def on_click(b, p=profile):
                self.selected_profile = p
                print(json.dumps(p))
                win.close()
                self.quit()

            btn.connect("clicked", on_click)
            row.add_suffix(btn)
            row.set_activatable_widget(btn)
            list_box.append(row)

        clamp.set_child(list_box)
        main_box.append(clamp)
        win.set_content(main_box)
        win.present()


def main():
    home_dir = Path(os.environ.get("HOME", "/root"))
    profiles_file = home_dir / ".rdp_profiles.json"

    if not profiles_file.exists():
        logger.error(f"Profiles file not found: {profiles_file}")
        sys.exit(1)

    try:
        with open(profiles_file, "r") as f:
            profiles = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read profiles: {e}")
        sys.exit(1)

    if not profiles:
        logger.error("No profiles found in profiles.json")
        sys.exit(1)

    # Check command line arguments if profile specified
    if len(sys.argv) > 1:
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
