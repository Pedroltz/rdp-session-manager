#!/usr/bin/env python3
"""
Connection Sources Management Dialog
Allows adding, editing, deleting, and exporting connection profiles for an RDP user.
"""

import uuid
import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib

from core.user_manager import ConnectionProfile, RDPUser
from utils.polkit import get_privilege_command

logger = logging.getLogger(__name__)


@Gtk.Template(filename=str(Path(__file__).parent.parent.parent / "data" / "ui" / "connection-sources-dialog.ui"))
class ConnectionSourcesDialog(Adw.Dialog):
    __gtype_name__ = 'ConnectionSourcesDialog'

    profiles_group = Gtk.Template.Child()
    close_button = Gtk.Template.Child()
    add_profile_button = Gtk.Template.Child()

    def __init__(self, parent, user_manager, rdp_user: RDPUser, **kwargs):
        super().__init__(**kwargs)
        self.user_manager = user_manager
        self.rdp_user = rdp_user
        self.parent = parent

        self.close_button.connect('clicked', lambda b: self.close())
        self.add_profile_button.connect('clicked', self.on_add_profile_clicked)

        self.load_profiles()

    def load_profiles(self):
        """Loads and renders profile rows"""
        # Cleanly remove previously added rows
        if hasattr(self, '_added_rows'):
            for row in self._added_rows:
                try:
                    self.profiles_group.remove(row)
                except Exception as e:
                    logger.debug(f"Error removing row: {e}")
        self._added_rows = []

        for profile in self.rdp_user.profiles:
            row = Adw.ActionRow()
            row.set_title(profile.name)

            if profile.profile_type == 'desktop':
                row.set_subtitle(f"Full Desktop ({profile.desktop_env.upper()})")
                row.set_icon_name("computer-symbolic")
            elif profile.profile_type == 'remoteapp':
                row.set_subtitle(f"RemoteApp Linux: {profile.app_command}")
                row.set_icon_name("application-x-executable-symbolic")
            elif profile.profile_type == 'winege-remoteapp':
                exe_name = Path(profile.app_command).name
                if profile.windows_app_id:
                    row.set_subtitle(
                        f"Windows (UMU/WineGE): {exe_name or profile.windows_app_id}"
                    )
                else:
                    row.set_subtitle(f"WineGE legacy: {exe_name}")
                row.set_icon_name("application-x-executable-symbolic")

            if profile.is_default:
                badge = Gtk.Label(label="Default")
                badge.add_css_class("accent")
                badge.add_css_class("caption")
                badge.set_valign(Gtk.Align.CENTER)
                row.add_suffix(badge)
            else:
                set_def_btn = Gtk.Button()
                set_def_btn.set_icon_name("emblem-favorite-symbolic")
                set_def_btn.set_tooltip_text("Make Default")
                set_def_btn.set_valign(Gtk.Align.CENTER)
                set_def_btn.connect('clicked', lambda b, p=profile: self.on_set_default_profile(p))
                row.add_suffix(set_def_btn)

            # Export button
            export_btn = Gtk.Button()
            export_btn.set_icon_name("document-save-symbolic")
            export_btn.set_tooltip_text("Export .rdp file")
            export_btn.set_valign(Gtk.Align.CENTER)
            export_btn.connect('clicked', lambda b, p=profile: self.on_export_profile(p))
            row.add_suffix(export_btn)

            # Delete button (only if more than 1 profile)
            if len(self.rdp_user.profiles) > 1:
                del_btn = Gtk.Button()
                del_btn.set_icon_name("user-trash-symbolic")
                del_btn.add_css_class("destructive-action")
                del_btn.set_valign(Gtk.Align.CENTER)
                del_btn.connect('clicked', lambda b, p=profile: self.on_delete_profile(p))
                row.add_suffix(del_btn)

            self.profiles_group.add(row)
            self._added_rows.append(row)

    def on_set_default_profile(self, target_profile: ConnectionProfile):
        """Sets target profile as default and unsets others"""
        for p in self.rdp_user.profiles:
            p.is_default = (p.profile_id == target_profile.profile_id)
        self.user_manager.save_profiles_for_user(self.rdp_user.username, self.rdp_user.profiles)
        self.load_profiles()
        if hasattr(self.parent, 'load_users'):
            self.parent.load_users()

    def on_export_profile(self, profile: ConnectionProfile):
        """Shows file chooser dialog to save .rdp file"""
        dialog = Gtk.FileDialog()
        dialog.set_initial_name(f"{self.rdp_user.username}_{profile.profile_id}.rdp")
        dialog.save(self.parent, None, self._on_export_dialog_finish, profile)

    def _on_export_dialog_finish(self, dialog, result, profile):
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                self.user_manager.export_rdp_file(self.rdp_user.username, profile.profile_id, path)
        except Exception as e:
            logger.error(f"Error or canceled saving .rdp file: {e}")

    def on_delete_profile(self, profile: ConnectionProfile):
        """Removes a profile"""
        self.rdp_user.profiles = [p for p in self.rdp_user.profiles if p.profile_id != profile.profile_id]
        if profile.is_default and self.rdp_user.profiles:
            self.rdp_user.profiles[0].is_default = True
        self.user_manager.save_profiles_for_user(self.rdp_user.username, self.rdp_user.profiles)
        self.load_profiles()
        if hasattr(self.parent, 'load_users'):
            self.parent.load_users()

    def on_add_profile_clicked(self, button):
        """Shows dialog to create a new profile"""
        dialog = ProfileEditDialog(self, self.rdp_user)
        dialog.connect('profile-saved', self.on_profile_added)
        dialog.present(self)

    def on_profile_added(self, dialog, profile: ConnectionProfile):
        if not self.rdp_user.profiles:
            profile.is_default = True
        self.rdp_user.profiles.append(profile)
        self.user_manager.save_profiles_for_user(
            self.rdp_user.username, self.rdp_user.profiles
        )
        self.load_profiles()
        if hasattr(self.parent, 'load_users'):
            self.parent.load_users()
        if profile.profile_type == 'winege-remoteapp' and profile.app_command:
            self._install_windows_profile(profile)

    def _install_windows_profile(self, profile: ConnectionProfile):
        """Start staging outside the GTK thread; authorization remains graphical."""
        rdpsm = shutil.which("rdpsm")
        if rdpsm:
            command = [
                rdpsm, "windows-app", "install", self.rdp_user.username,
                "--profile-id", profile.profile_id,
                "--source", profile.app_command,
                "--name", profile.name,
            ]
        else:
            cli = Path(__file__).resolve().parents[1] / "cli.py"
            command = [sys.executable, str(cli), "windows-app", "install",
                       self.rdp_user.username, "--profile-id", profile.profile_id,
                       "--source", profile.app_command, "--name", profile.name]
        _, privilege = get_privilege_command()

        def worker():
            result = subprocess.run(
                privilege + command, capture_output=True, text=True, timeout=1800
            )
            GLib.idle_add(self._windows_install_finished, profile, result)

        threading.Thread(target=worker, daemon=True).start()

    def _windows_install_finished(self, profile, result):
        if result.returncode == 0:
            refreshed = self.user_manager.get_user(self.rdp_user.username)
            if refreshed:
                self.rdp_user = refreshed
                self.load_profiles()
            logger.info("Windows application prepared for profile %s", profile.profile_id)
            message = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Windows application prepared",
                body=(
                    "The isolated prefix and connection profile were created.\n\n"
                    "If the installer needs interaction, connect through this RDP "
                    "profile to finish it."
                ),
            )
        else:
            logger.error(
                "Windows application setup failed for %s: %s",
                profile.profile_id,
                result.stderr.strip(),
            )
            message = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Windows application setup failed",
                body=result.stderr.strip() or "See the RDPSM logs for details.",
            )
        message.add_response("ok", "OK")
        message.present()
        return False


class ProfileEditDialog(Adw.Dialog):
    """Dialog to configure a new connection profile"""

    __gsignals__ = {
        'profile-saved': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, parent, rdp_user: RDPUser, **kwargs):
        super().__init__(**kwargs)
        self.rdp_user = rdp_user

        self.set_title("Add Connection Source")
        self.set_content_width(450)
        self.set_content_height(450)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect('clicked', lambda b: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Add")
        save_btn.add_css_class("suggested-action")
        save_btn.connect('clicked', self.on_save)
        header.pack_end(save_btn)
        main_box.append(header)

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()

        # Name
        self.name_row = Adw.EntryRow(title="Source Name")
        group.add(self.name_row)

        # Type Combo
        self.type_combo = Adw.ComboRow(title="Connection Type")
        model = Gtk.StringList()
        model.append("Full Desktop")
        model.append("RemoteApp (Linux)")
        model.append("Windows App (umu)")
        self.type_combo.set_model(model)
        group.add(self.type_combo)

        # DE Combo
        self.de_combo = Adw.ComboRow(title="Desktop Environment")
        de_model = Gtk.StringList()
        de_model.append("XFCE")
        de_model.append("GNOME")
        de_model.append("KDE")
        self.de_combo.set_model(de_model)
        group.add(self.de_combo)

        # App Command
        self.cmd_row = Adw.EntryRow(title="App Command / Windows Installer")
        group.add(self.cmd_row)

        # App Args
        self.args_row = Adw.EntryRow(title="App Arguments")
        group.add(self.args_row)

        page.add(group)
        main_box.append(page)
        self.set_child(main_box)

        # Signal for type combo change
        self.type_combo.connect("notify::selected", self.on_type_changed)
        self.on_type_changed(self.type_combo, None)

    def on_type_changed(self, combo, pspec):
        sel = combo.get_selected()
        if sel == 0:  # Desktop
            self.de_combo.set_visible(True)
            self.cmd_row.set_visible(False)
            self.args_row.set_visible(False)
        else:  # RemoteApp / WineGE
            self.de_combo.set_visible(False)
            self.cmd_row.set_visible(True)
            self.args_row.set_visible(True)

    def on_save(self, btn):
        name = self.name_row.get_text().strip() or "New Connection Source"
        sel_type = self.type_combo.get_selected()
        p_type = "desktop" if sel_type == 0 else ("remoteapp" if sel_type == 1 else "winege-remoteapp")
        
        sel_de = self.de_combo.get_selected()
        desktop_env = "xfce" if sel_de == 0 else ("gnome" if sel_de == 1 else "kde")

        cmd = self.cmd_row.get_text().strip()
        args = self.args_row.get_text().strip()

        profile = ConnectionProfile(
            profile_id=str(uuid.uuid4())[:8],
            name=name,
            profile_type=p_type,
            desktop_env=desktop_env,
            app_command=cmd,
            app_args=args,
            is_default=False
        )

        self.emit('profile-saved', profile)
        self.close()
