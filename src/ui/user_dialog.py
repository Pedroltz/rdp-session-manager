#!/usr/bin/env python3
"""
User Creation Dialog
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, GLib
import logging
import threading
from pathlib import Path

from utils.validator import Validator

logger = logging.getLogger(__name__)


@Gtk.Template(filename=str(Path(__file__).parent.parent.parent / "data" / "ui" / "user-dialog.ui"))
class UserDialog(Adw.Dialog):
    __gtype_name__ = 'UserDialog'

    __gsignals__ = {
        'user-created': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    # UI elements from template
    username_entry = Gtk.Template.Child()
    fullname_entry = Gtk.Template.Child()
    password_entry = Gtk.Template.Child()
    confirm_password_entry = Gtk.Template.Child()
    session_type_combo = Gtk.Template.Child()
    desktop_container = Gtk.Template.Child()
    desktop_group = Gtk.Template.Child()
    de_combo = Gtk.Template.Child()
    install_de_switch = Gtk.Template.Child()
    remoteapp_container = Gtk.Template.Child()
    remoteapp_group = Gtk.Template.Child()
    app_combo = Gtk.Template.Child()
    custom_app_entry = Gtk.Template.Child()
    app_args_entry = Gtk.Template.Child()
    winege_container = Gtk.Template.Child()
    winege_group = Gtk.Template.Child()
    exe_file_button = Gtk.Template.Child()
    exe_path_entry = Gtk.Template.Child()
    auto_start_switch = Gtk.Template.Child()
    create_button = Gtk.Template.Child()
    cancel_button = Gtk.Template.Child()

    def __init__(self, parent, user_manager, rdp_config, de_installer, **kwargs):
        super().__init__(**kwargs)

        self.user_manager = user_manager
        self.rdp_config = rdp_config
        self.de_installer = de_installer

        self.setup_signals()
        self.setup_session_type_combo()
        self.setup_de_combo()
        self.setup_app_combo()

    def setup_signals(self):
        """Setup signal handlers"""
        self.create_button.connect('clicked', self.on_create_user)
        self.cancel_button.connect('clicked', lambda b: self.close())
        self.exe_file_button.connect('clicked', self.on_select_exe_file)

        # Enable/disable create button based on validation
        self.username_entry.connect('changed', lambda e: self.validate_form())
        self.password_entry.connect('changed', lambda e: self.validate_form())
        self.confirm_password_entry.connect('changed', lambda e: self.validate_form())
        self.exe_path_entry.connect('changed', lambda e: self.validate_form())

    def setup_session_type_combo(self):
        """Setup session type combo (Desktop vs RemoteApp vs WineGE)"""
        string_list = Gtk.StringList()
        string_list.append("Full Desktop")
        string_list.append("RemoteApp (Linux Application)")
        string_list.append("WineGE RemoteApp (Windows Application)")

        self.session_type_combo.set_model(string_list)
        self.session_type_combo.set_selected(0)  # Default: Desktop

        # Connect signal to toggle visibility
        self.session_type_combo.connect('notify::selected', self.on_session_type_changed)

    def setup_de_combo(self):
        """Setup desktop environment combo"""
        # Get available DEs
        des = self.de_installer.get_available_des()

        # Create a string list model
        string_list = Gtk.StringList()

        # Map combo index to DE id
        self.de_map = {}

        for idx, de in enumerate(des):
            # Add to combo with installation status
            installed_mark = " OK" if de['installed'] else ""
            label = f"{de['name']} (~{de['size_mb']}MB){installed_mark}"
            string_list.append(label)

            # Map index to DE id
            self.de_map[idx] = de['id']

        # Set the model to the combo box
        self.de_combo.set_model(string_list)

        # Set default selection to first item (usually the lightest DE)
        self.de_combo.set_selected(0)

    def setup_app_combo(self):
        """Setup RemoteApp application combo"""
        # We no longer need the combo, just the input field
        # Hide the combo and always show the custom field
        self.app_combo.set_visible(False)
        self.custom_app_entry.set_visible(True)

    def on_session_type_changed(self, combo, param):
        """Handle session type change"""
        selected = combo.get_selected()

        if selected == 0: # Full Desktop
            self.desktop_container.set_visible(True)
            self.remoteapp_container.set_visible(False)
            self.winege_container.set_visible(False)
        elif selected == 1:  # RemoteApp (Linux)
            self.desktop_container.set_visible(False)
            self.remoteapp_container.set_visible(True)
            self.winege_container.set_visible(False)
        else:  # WineGE RemoteApp (Windows)
            self.desktop_container.set_visible(False)
            self.remoteapp_container.set_visible(False)
            self.winege_container.set_visible(True)

    def on_select_exe_file(self, button):
        """Open file chooser dialog to select .exe file"""
        from gi.repository import Gio

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Windows Executable")

        # Create file filter for .exe files
        filter_exe = Gtk.FileFilter()
        filter_exe.set_name("Windows executables (*.exe)")
        filter_exe.add_pattern("*.exe")
        filter_exe.add_pattern("*.EXE")

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_exe)
        filters.append(filter_all)

        dialog.set_filters(filters)
        dialog.set_default_filter(filter_exe)

        # Open dialog - get root window
        root = self.get_root()
        dialog.open(root, None, self.on_exe_file_selected)

    def on_exe_file_selected(self, dialog, result):
        """Handle file selection"""
        try:
            file = dialog.open_finish(result)
            if file:
                # Get file path (not URI)
                path = file.get_path()

                # If get_path() returns None, try to decode the URI
                if not path:
                    import urllib.parse
                    uri = file.get_uri()
                    # Remove 'file://' and decode
                    path = urllib.parse.unquote(uri.replace('file://', ''))

                # Ensure the path is absolute
                if not path.startswith('/'):
                    path = '/' + path

                self.exe_path_entry.set_text(path)
                logger.info(f"Selected .exe file: {path}")
        except Exception as e:
            # Ignore error when user cancels dialog
            error_msg = str(e)
            if "No file selected" not in error_msg and "dismissed" not in error_msg.lower():
                logger.error(f"Error selecting file: {e}")


    def validate_form(self):
        """Validate form inputs"""
        username = self.username_entry.get_text()
        password = self.password_entry.get_text()
        confirm = self.confirm_password_entry.get_text()

        # Validate username
        valid_username, username_error = Validator.validate_username(username)

        if not valid_username and username:
            self.username_entry.add_css_class('error')
        else:
            self.username_entry.remove_css_class('error')

        # Validate password
        valid_password, password_error = Validator.validate_password(password, confirm)

        if not valid_password and password:
            self.password_entry.add_css_class('error')
            self.confirm_password_entry.add_css_class('error')
        else:
            self.password_entry.remove_css_class('error')
            self.confirm_password_entry.remove_css_class('error')

        # Enable create button if all valid
        all_valid = valid_username and valid_password
        self.create_button.set_sensitive(all_valid)

        return all_valid

    def on_create_user(self, button):
        """Handle user creation"""
        logger.info("=" * 60)
        logger.info("START OF RDP USER CREATION")
        logger.info("=" * 60)

        if not self.validate_form():
            logger.warning("Invalid form - creation aborted")
            return

        # Get form data
        username = self.username_entry.get_text()
        fullname = self.fullname_entry.get_text()
        password = self.password_entry.get_text()

        # Get session type
        session_type_idx = self.session_type_combo.get_selected()
        if session_type_idx == 0:
            session_type = 'desktop'
        elif session_type_idx == 1:
            session_type = 'remoteapp'
        else:
            session_type = 'winege-remoteapp'

        logger.info(f"Form data:")
        logger.info(f"  - Username: {username}")
        logger.info(f"  - Fullname: {fullname}")
        logger.info(f"  - Session Type: {session_type}")

        # Get DE or App based on session type
        if session_type == 'desktop':
            de_idx = self.de_combo.get_selected()
            de_id = self.de_map.get(de_idx, 'xfce')
            app_command = ''
            app_args = ''

            logger.info(f"  - DE Index: {de_idx}")
            logger.info(f"  - DE ID: {de_id}")

            auto_start = self.auto_start_switch.get_active()
            install_de = self.install_de_switch.get_active()

            logger.info(f"  - Auto-start: {auto_start}")
            logger.info(f"  - Install DE: {install_de}")
        elif session_type == 'remoteapp':
            de_id = 'xfce' # Default DE (will not be used)
            install_de = False

            # Get app command directly from custom entry
            app_command = self.custom_app_entry.get_text().strip()
            app_args = self.app_args_entry.get_text().strip()

            logger.info(f"  - App Command: {app_command}")
            logger.info(f"  - App Args: {app_args}")
        else:  # winege-remoteapp
            de_id = 'xfce' # Default DE (will not be used)
            install_de = False

            # Get .exe path
            app_command = self.exe_path_entry.get_text().strip()
            app_args = '' # WineGE does not use separate arguments

            logger.info(f"  - EXE Path: {app_command}")

            # Validate if .exe file exists
            from pathlib import Path
            if not Path(app_command).exists():
                logger.error(f"Exe file not found: {app_command}")
                error_dialog = Adw.MessageDialog(
                    transient_for=self.get_root(),
                    heading="File not found",
                    body=f"The executable file was not found:\n\n{app_command}\n\nPlease select a valid file."
                )
                error_dialog.add_response("ok", "OK")
                error_dialog.present()
                return

        # Check if DE needs installation
        de_installed = self.de_installer.is_de_installed(de_id)
        logger.info(f"  - DE '{de_id}' already installed: {de_installed}")

        # For RemoteApp and WineGE, no need to install DE
        if session_type in ['remoteapp', 'winege-remoteapp']:
            logger.info(f"→ Creating user {session_type} directly")
            self.create_user(username, password, fullname, de_id, session_type, app_command, app_args)
        elif install_de and not de_installed:
            logger.info(f"→ Desktop Environment '{de_id}' needs to be installed first")
            self.install_de_and_create_user(de_id, username, password, fullname, session_type, app_command, app_args)
        else:
            if not de_installed:
                logger.warning(f"WARNING '{de_id}' is not installed but user chose not to install")
            logger.info(f"→ Creating user directly (DE installation: {install_de})")
            self.create_user(username, password, fullname, de_id, session_type, app_command, app_args)

    def install_de_and_create_user(self, de_id, username, password, fullname,
                                   session_type='desktop', app_command='', app_args=''):
        """Install DE and then create user"""
        logger.info(f"→ STARTING DESKTOP ENVIRONMENT INSTALLATION: {de_id}")

        # Get DE info
        de_info = self.de_installer.get_de_info(de_id)
        de_name = de_info['name'] if de_info else de_id.upper()

        logger.info(f"  - Name: {de_name}")
        if de_info:
            logger.info(f"  - Size: ~{de_info['size_mb']} MB")
            logger.info(f"  - Packages: {', '.join(de_info['packages'])}")

        # Show progress dialog with terminal log
        progress_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=f"Installing {de_name}",
            body=f"Installing Desktop Environment...\nThis may take several minutes."
        )

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_size_request(700, 400)

        # Spinner and status
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_halign(Gtk.Align.CENTER)

        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_size_request(32, 32)
        header_box.append(spinner)

        status_label = Gtk.Label(label="Preparing installation...")
        status_label.add_css_class('title-3')
        header_box.append(status_label)

        main_box.append(header_box)

        # Expander to show/hide terminal
        expander = Gtk.Expander()
        expander.set_label("📜 View Installation Log")
        expander.set_expanded(True) # Expanded by default

        # Terminal log view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(300)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_monospace(True)
        text_view.add_css_class('terminal-log')

        # CSS for terminal appearance
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        .terminal-log {
            background-color: #2e3436;
            color: #d3d7cf;
            padding: 12px;
            font-family: monospace;
            font-size: 10pt;
        }
        """)
        text_view.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        text_buffer = text_view.get_buffer()
        scrolled.set_child(text_view)
        expander.set_child(scrolled)
        main_box.append(expander)

        progress_dialog.set_extra_child(main_box)
        progress_dialog.present()

        def append_log(message):
            """Append message to log"""
            end_iter = text_buffer.get_end_iter()
            text_buffer.insert(end_iter, f"{message}\n", -1)
            # Auto scroll to bottom
            mark = text_buffer.create_mark(None, text_buffer.get_end_iter(), False)
            text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        def update_status(text):
            """Update status label"""
            status_label.set_label(text)

        # Install DE async
        def on_install_complete(success, message):
            spinner.stop()

            if success:
                logger.info(f"OK Installation of {de_name} completed SUCCESSFULLY")
                append_log("OK Installation completed successfully!")
                update_status("OK Installation complete!")

                # Wait and then create user
                logger.info("→ Waiting 1.5s before creating user...")
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.create_user(username, password, fullname, de_id, session_type, app_command, app_args))
            else:
                logger.error(f"X ERROR installing {de_name}: {message}")
                append_log(f"X ERROR: {message}")
                update_status("X Installation error")

                # Wait and show error dialog
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_de_install_error(message, username, password, fullname, de_id, session_type, app_command, app_args))

        def install_in_thread():
            try:
                GLib.idle_add(append_log, f"=== Installing {de_name} ===")
                GLib.idle_add(append_log, f"DE ID: {de_id}")

                if de_info:
                    GLib.idle_add(append_log, f"Estimated size: ~{de_info['size_mb']} MB")
                    GLib.idle_add(append_log, f"Packages: {', '.join(de_info['packages'][:3])}...")

                GLib.idle_add(append_log, "")
                GLib.idle_add(update_status, "Checking disk space...")

                success, message = self.de_installer.install_de(
                    de_id,
                    progress_callback=lambda progress, msg: GLib.idle_add(self._handle_de_progress, append_log, update_status, progress, msg)
                )

                GLib.idle_add(on_install_complete, success, message)

            except Exception as e:
                logger.error(f"Error installing DE: {e}")
                GLib.idle_add(on_install_complete, False, str(e))

        thread = threading.Thread(target=install_in_thread)
        thread.daemon = True
        thread.start()

    def _handle_de_progress(self, append_log, update_status, progress, message):
        """Handle DE installation progress"""
        append_log(message)
        if progress == 10:
            update_status("Updating package cache...")
        elif progress == 30:
            update_status("Downloading and installing packages...")
        elif progress == 100:
            update_status("Finishing installation...")

    def show_de_install_error(self, message, username, password, fullname, de_id,
                              session_type='desktop', app_command='', app_args=''):
        """Show DE installation error dialog"""
        error_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Installation Error",
            body=f"{message}\n\nYou can continue without installing the Desktop Environment if it is already available."
        )
        error_dialog.add_response("cancel", "Cancel")
        error_dialog.add_response("continue", "Continue Anyway")
        error_dialog.set_response_appearance("continue", Adw.ResponseAppearance.SUGGESTED)
        error_dialog.connect("response", lambda d, r: self.handle_install_error(r, username, password, fullname, de_id, session_type, app_command, app_args))
        error_dialog.present()

    def handle_install_error(self, response, username, password, fullname, de_id,
                            session_type='desktop', app_command='', app_args=''):
        """Handle installation error response"""
        if response == "continue":
            self.create_user(username, password, fullname, de_id, session_type, app_command, app_args)

    def create_user(self, username, password, fullname, de_id,
                   session_type='desktop', app_command='', app_args=''):
        """Create the user"""
        logger.info("=" * 60)
        logger.info(f"→ STARTING USER CREATION: {username}")
        logger.info(f"  - Session Type: {session_type}")
        if session_type == 'desktop':
            logger.info(f"  - Desktop Environment: {de_id}")
        else:
            logger.info(f"  - App Command: {app_command} {app_args}")
        logger.info("=" * 60)

        # Show progress with terminal log
        # Special message to WineGE
        if session_type == 'winege-remoteapp':
            body_text = f"Creating user {username}...\n\nWarning: WineGE RemoteApp requires a ~750 MB download.\nThe first setup may take 10–15 minutes.\nPlease wait and do not close this window."
        else:
            body_text = f"Creating user {username}..."

        progress_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Creating RDP User",
            body=body_text
        )

        # Create container with spinner and log
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        progress_box.set_size_request(600, 300)

        # Spinner
        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_size_request(-1, 32)
        progress_box.append(spinner)

        # Terminal log view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(250)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_monospace(True)
        text_view.add_css_class('terminal-log')

        # CSS for terminal appearance
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        .terminal-log {
            background-color: #2e3436;
            color: #d3d7cf;
            padding: 12px;
            font-family: monospace;
            font-size: 11pt;
        }
        """)
        text_view.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        text_buffer = text_view.get_buffer()
        scrolled.set_child(text_view)
        progress_box.append(scrolled)

        progress_dialog.set_extra_child(progress_box)
        progress_dialog.present()

        def append_log(message):
            """Append message to log"""
            end_iter = text_buffer.get_end_iter()
            text_buffer.insert(end_iter, f"{message}\n", -1)
            # Auto scroll to bottom
            mark = text_buffer.create_mark(None, text_buffer.get_end_iter(), False)
            text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        def on_create_complete(success, user_or_error):
            spinner.stop()

            if success:
                user = user_or_error
                logger.info(f"OK USER {username} CREATED SUCCESSFULLY!")
                logger.info(f"  - UID: {user.uid}")
                logger.info(f"  - RDP Port: {user.rdp_port}")
                logger.info(f"  - Home: {user.home_dir}")
                logger.info(f"  - DE: {user.desktop_env}")
                append_log("OK User created successfully!")

                # Wait a bit before closing
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_success_dialog(username, fullname, de_id, user))
            else:
                error = user_or_error
                logger.error(f"X ERROR WHILE CREATING USER {username}: {error}")
                append_log(f"X ERROR: {error}")

                # Wait before showing error dialog
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_error_dialog(error))

        def create_in_thread():
            try:
                GLib.idle_add(append_log, "=== Creating RDP User ===")
                GLib.idle_add(append_log, f"User: {username}")

                if session_type == 'desktop':
                    GLib.idle_add(append_log, f"Type: Full Desktop")
                    GLib.idle_add(append_log, f"Desktop Environment: {de_id.upper()}")
                elif session_type == 'remoteapp':
                    GLib.idle_add(append_log, "Type: RemoteApp (Linux)")
                    GLib.idle_add(append_log, f"Application: {app_command}")
                elif session_type == 'winege-remoteapp':
                    GLib.idle_add(append_log, "Type: WineGE RemoteApp (Windows)")
                    GLib.idle_add(append_log, f"Executable: {app_command}")
                    GLib.idle_add(append_log, "")
                    GLib.idle_add(append_log, "WARNING: The first WineGE setup takes 10–15 minutes")
                    GLib.idle_add(append_log, "Download: ~750 MB | Extraction and configuration")
                    GLib.idle_add(append_log, "Please wait and do not close this window")

                GLib.idle_add(append_log, "")

                # Create user with log callback
                GLib.idle_add(append_log, "→ Checking group rdp-users...")
                user = self.user_manager.create_user(
                    username=username,
                    password=password,
                    desktop_env=de_id,
                    full_name=fullname,
                    session_type=session_type,
                    app_command=app_command,
                    app_args=app_args,
                    log_callback=lambda msg: GLib.idle_add(append_log, msg)
                )

                if user:
                    GLib.idle_add(append_log, "")
                    GLib.idle_add(append_log, "→ Configuring RDP session...")

                    # Configure RDP session
                    self.rdp_config.create_user_session(
                        username=username,
                        uid=user.uid,
                        desktop_env=de_id,
                        rdp_port=user.rdp_port
                    )

                    GLib.idle_add(append_log, f"  RDP Port: {user.rdp_port}")
                    GLib.idle_add(append_log, f"  UID: {user.uid}")
                    GLib.idle_add(append_log, "Configuration complete!")

                    GLib.idle_add(on_create_complete, True, user)
                else:
                    GLib.idle_add(on_create_complete, False, "Failed to create user")

            except Exception as e:
                logger.error(f"Error creating user: {e}")
                GLib.idle_add(on_create_complete, False, str(e))

        thread = threading.Thread(target=create_in_thread)
        thread.daemon = True
        thread.start()

    def show_success_dialog(self, username, fullname, de_id, user):
        """Show success dialog"""
        # Build information based on session type
        if user.session_type == 'desktop':
            session_info = f"Desktop: {de_id.upper()}"
        elif user.session_type == 'remoteapp':
            session_info = f"Type: RemoteApp (Linux)\nApplication: {user.app_command}"
        elif user.session_type == 'winege-remoteapp':
            session_info = f"Type: WineGE RemoteApp (Windows)\nExecutable: {user.app_command}"
        else:
            session_info = f"Type: {user.session_type}"

        success_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="User Created Successfully!",
            body=f"""User: {username}
Name: {fullname or username}
{session_info}
RDP port: {user.rdp_port}

<b>How to Connect:</b>

Address: {self.get_connection_info(user.rdp_port)}

Linux:
  xfreerdp /v:{self.get_connection_info(user.rdp_port)} /u:{username}

Windows:
  Use "Remote Desktop Connection"
  Digite: {self.get_connection_info(user.rdp_port)}

The user already appears in the main list!"""
        )
        success_dialog.set_body_use_markup(True)

        success_dialog.add_response("ok", "Close")
        success_dialog.connect("response", lambda d, r: self.close())
        success_dialog.present()

        # Emit signal
        self.emit('user-created')
        logger.info(f"User {username} created successfully")

    def show_error_dialog(self, error):
        """Show error dialog"""
        error_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Error creating user",
            body=f"Unable to create user.\n\nError: {error}\n\nCheck:\n• You have administrator permissions\n• The username does not exist\n• The group rdp-users was created"
        )
        error_dialog.add_response("ok", "OK")
        error_dialog.present()

    def get_connection_info(self, port):
        """Get connection information"""
        from core.session_monitor import SessionMonitor

        monitor = SessionMonitor()
        ips = monitor.get_all_network_ips()

        if ips:
            return f"{ips[0]}:{port}"
        return f"localhost:{port}"
