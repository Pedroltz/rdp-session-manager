#!/usr/bin/env python3
"""
RDP Session Manager - Command Line Interface
"""

import sys
import argparse
import logging
import time
from typing import Optional
from pathlib import Path

from core.user_manager import UserManager
from core.session_monitor import SessionMonitor
from core.de_installer import DEInstaller
from core.desktop_environments import SUPPORTED_DESKTOPS, normalize_desktop_id
from core.system_deps import SystemDependencies
from core.config import AppConfig
from core.server_manager import ServerManager
from core.windows_runtime import WindowsRuntimeMigrator
from utils.logger import setup_logger
from utils.polkit import get_privilege_command, set_cli_mode
from version import __version__

# Ativar modo CLI - força uso de sudo ao invés de pkexec
set_cli_mode(True)

logger = logging.getLogger(__name__)


class CLI:
    """Command Line Interface for RDP Session Manager"""

    def __init__(self):
        # Keep server diagnostics genuinely headless and read-only. Components
        # that touch an administrator's home are created only by commands that
        # actually need them.
        self._app_config = None
        self._user_manager = None
        self._session_monitor = None
        self._de_installer = None
        self._system_deps = None
        self.server_manager = ServerManager()
        self.windows_migrator = WindowsRuntimeMigrator()

        # Colors for terminal output
        self.RESET = '\033[0m'
        self.RED = '\033[91m'
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'

        # Disable colors if output is not a TTY
        if not sys.stdout.isatty():
            self.RESET = self.RED = self.GREEN = self.YELLOW = ''
            self.BLUE = self.CYAN = self.BOLD = ''

    @property
    def app_config(self):
        if self._app_config is None:
            self._app_config = AppConfig()
        return self._app_config

    @property
    def user_manager(self):
        if self._user_manager is None:
            self._user_manager = UserManager(self.app_config)
        return self._user_manager

    @property
    def session_monitor(self):
        if self._session_monitor is None:
            self._session_monitor = SessionMonitor()
        return self._session_monitor

    @property
    def de_installer(self):
        if self._de_installer is None:
            self._de_installer = DEInstaller()
        return self._de_installer

    @property
    def system_deps(self):
        if self._system_deps is None:
            self._system_deps = SystemDependencies()
        return self._system_deps

    def print_success(self, message: str):
        """Print success message"""
        print(f"{self.GREEN}OK{self.RESET} {message}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"{self.RED}X{self.RESET} {message}", file=sys.stderr)

    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{self.YELLOW}!{self.RESET} {message}")

    def print_info(self, message: str):
        """Print info message"""
        print(f"{self.BLUE}→{self.RESET} {message}")

    def print_header(self, message: str):
        """Print header"""
        print(f"\n{self.BOLD}{self.CYAN}{message}{self.RESET}")
        print(f"{self.CYAN}{'=' * len(message)}{self.RESET}")

    # ==================== USER COMMANDS ====================

    def user_create(self, args):
        """Create a new RDP user"""
        try:
            import getpass

            username = args.username
            full_name = args.fullname or ""
            session_type = args.session_type or "desktop"

            # RemoteApp parameters
            app_command = args.app_command or ""
            app_args = args.app_args or ""

            # Desktop environment (only for desktop sessions)
            desktop_env = normalize_desktop_id(args.desktop or "xfce")

            # Validate session type
            if session_type not in ['desktop', 'remoteapp', 'winege-remoteapp']:
                self.print_error(f"Invalid session type '{session_type}'. Must be 'desktop', 'remoteapp', or 'winege-remoteapp'")
                return 1

            # Validate RemoteApp parameters
            if session_type == 'remoteapp':
                if not app_command:
                    self.print_error("RemoteApp session requires --app-command parameter")
                    self.print_info("Example: rdpsm user create USERNAME --session-type remoteapp --app-command firefox")
                    return 1

            # Validate WineGE RemoteApp parameters
            if session_type == 'winege-remoteapp':
                if not app_command:
                    self.print_error("Windows RemoteApp requires --app-command with an .exe path")
                    self.print_info("Example: rdpsm user create USERNAME --session-type winege-remoteapp --app-command /path/to/app.exe")
                    return 1

                # Verificar se o arquivo .exe existe
                from pathlib import Path
                exe_path = Path(app_command)
                if not exe_path.exists():
                    self.print_error(f"Executable file not found: {app_command}")
                    return 1

                if not app_command.lower().endswith('.exe'):
                    self.print_warning(f"Warning: File does not have .exe extension: {app_command}")
                    self.print_info("Proceeding anyway, but make sure this is a Windows executable")

            # Get password
            if args.password:
                password = args.password
                confirm = args.password
            else:
                password = getpass.getpass(f"Password for {username}: ")
                confirm = getpass.getpass("Confirm password: ")

            if password != confirm:
                self.print_error("Passwords do not match")
                return 1

            # For desktop sessions, check if Desktop Environment is installed
            if session_type == 'desktop':
                if desktop_env not in SUPPORTED_DESKTOPS:
                    self.print_error(
                        f"Unsupported desktop environment '{args.desktop}'. "
                        f"Options: {', '.join(SUPPORTED_DESKTOPS)}"
                    )
                    return 1
                de_installed = self.de_installer.is_de_installed(desktop_env)

                if not de_installed:
                    self.print_warning(f"Desktop environment '{desktop_env}' is not installed")
                    self.print_info("Installing Desktop Environment first...")

                    # Check disk space
                    has_space, required, available = self.de_installer.check_disk_space(desktop_env)
                    if not has_space:
                        self.print_error(f"Insufficient disk space. Required: {required}MB, Available: {available}MB")
                        return 1

                    # Install DE
                    def progress_callback(progress, message):
                        if args.verbose:
                            print(f"  {message}")

                    self.print_info(f"Installing {desktop_env.upper()} desktop environment...")
                    success, message = self.de_installer.install_de(
                        desktop_env,
                        progress_callback=progress_callback
                    )

                    if not success:
                        self.print_error(f"Failed to install desktop environment: {message}")
                        return 1

                    self.print_success(f"Desktop environment '{desktop_env}' installed successfully")
                    print()  # Blank line for readability

                self.print_info(f"Creating user '{username}' with {desktop_env.upper()} desktop...")
            else:
                # RemoteApp session
                app_display = f"{app_command} {app_args}".strip()
                self.print_info(f"Creating RemoteApp user '{username}' with application: {app_display}")

            user = self.user_manager.create_user(
                username=username,
                password=password,
                desktop_env=desktop_env,
                full_name=full_name,
                session_type=session_type,
                app_command=app_command,
                app_args=app_args,
                log_callback=lambda msg: print(f"  {msg}") if args.verbose else None
            )

            if user:
                self.print_success(f"User '{username}' created successfully")
                self.print_info(f"UID: {user.uid}")
                self.print_info(f"Home: {user.home_dir}")
                self.print_info(f"RDP Port: {user.rdp_port}")
                if session_type == 'remoteapp':
                    self.print_info(f"Session Type: RemoteApp")
                    self.print_info(f"Application: {app_command} {app_args}".strip())
                else:
                    self.print_info(f"Session Type: Desktop ({desktop_env.upper()})")
                return 0
            else:
                self.print_error("Failed to create user")
                return 1

        except Exception as e:
            self.print_error(f"Error creating user: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def user_delete(self, args):
        """Delete an RDP user"""
        try:
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            # Confirmation
            if not args.force:
                response = input(f"Delete user '{username}' and all data? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    self.print_info("Cancelled")
                    return 0

            self.print_info(f"Deleting user '{username}'...")

            success = self.user_manager.delete_user(
                username=username,
                remove_home=True,
                kill_processes=True
            )

            if success:
                self.print_success(f"User '{username}' deleted successfully")
                return 0
            else:
                self.print_error("Failed to delete user")
                return 1

        except Exception as e:
            self.print_error(f"Error deleting user: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def user_list(self, args):
        """List all RDP users"""
        try:
            users = self.user_manager.list_users()

            if not users:
                self.print_info("No RDP users found")
                return 0

            if args.format == 'json':
                import json
                users_data = [user.to_dict() for user in users]
                print(json.dumps(users_data, indent=2))
            else:
                # Table format
                self.print_header(f"RDP Users ({len(users)} total)")

                # Header
                print(f"\n{self.BOLD}{'Username':<20} {'UID':<8} {'Desktop':<10} {'Port':<8} {'Status':<15}{self.RESET}")
                print("-" * 70)

                # Users
                for user in users:
                    status = "Disabled" if not user.enabled else "Enabled"
                    status_color = self.RED if not user.enabled else self.GREEN

                    print(
                        f"{user.username:<20} "
                        f"{user.uid:<8} "
                        f"{user.desktop_env.upper():<10} "
                        f"{user.rdp_port:<8} "
                        f"{status_color}{status:<15}{self.RESET}"
                    )

            return 0

        except Exception as e:
            self.print_error(f"Error listing users: {e}")
            return 1

    def user_info(self, args):
        """Show information about a specific user"""
        try:
            username = args.username
            user = self.user_manager.get_user(username)

            if not user:
                self.print_error(f"User '{username}' not found")
                return 1

            if args.format == 'json':
                import json
                print(json.dumps(user.to_dict(), indent=2))
            else:
                self.print_header(f"User Information: {username}")
                print(f"  Username:     {user.username}")
                print(f"  UID:          {user.uid}")
                print(f"  Home:         {user.home_dir}")
                print(f"  Session Type: {user.session_type}")

                if user.session_type == 'desktop':
                    print(f"  Desktop Env:  {user.desktop_env.upper()}")
                elif user.session_type in ['remoteapp', 'winege-remoteapp']:
                    print(f"  App Command:  {user.app_command}")
                    if user.app_args:
                        print(f"  App Args:     {user.app_args}")

                print(f"  RDP Port:     {user.rdp_port}")
                print(f"  Status:       {'Enabled' if user.enabled else 'Disabled'}")
                print(f"  Sudo Access:  {'Yes' if user.is_superuser else 'No'}")

                # Check if connected
                if self.session_monitor.is_user_connected(username):
                    session = self.session_monitor.get_user_session(username)
                    print(f"  Connected:    Yes (from {session.ip_address})")
                else:
                    print(f"  Connected:    No")

                # Process count
                processes = self.user_manager.get_user_processes(username)
                print(f"  Processes:    {len(processes)}")

            return 0

        except Exception as e:
            self.print_error(f"Error getting user info: {e}")
            return 1

    def user_enable(self, args):
        """Enable an RDP user"""
        try:
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            self.print_info(f"Enabling user '{username}'...")

            success = self.user_manager.unlock_user(username)

            if success:
                self.print_success(f"User '{username}' enabled")
                return 0
            else:
                self.print_error("Failed to enable user")
                return 1

        except Exception as e:
            self.print_error(f"Error enabling user: {e}")
            return 1

    def user_disable(self, args):
        """Disable an RDP user"""
        try:
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            self.print_info(f"Disabling user '{username}'...")

            success = self.user_manager.lock_user(username)

            if success:
                self.print_success(f"User '{username}' disabled")
                return 0
            else:
                self.print_error("Failed to disable user")
                return 1

        except Exception as e:
            self.print_error(f"Error disabling user: {e}")
            return 1

    def user_password(self, args):
        """Change user password"""
        try:
            import getpass

            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            # Get new password
            if args.password:
                password = args.password
            else:
                password = getpass.getpass(f"New password for {username}: ")
                confirm = getpass.getpass("Confirm password: ")

                if password != confirm:
                    self.print_error("Passwords do not match")
                    return 1

            self.print_info(f"Changing password for '{username}'...")

            success = self.user_manager.change_password(username, password)

            if success:
                self.print_success(f"Password changed for '{username}'")
                return 0
            else:
                self.print_error("Failed to change password")
                return 1

        except Exception as e:
            self.print_error(f"Error changing password: {e}")
            return 1

    def user_processes(self, args):
        """List user processes"""
        try:
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            processes = self.user_manager.get_user_processes(username)

            if not processes:
                self.print_info(f"No processes found for user '{username}'")
                return 0

            self.print_header(f"Processes for {username} ({len(processes)} total)")
            for pid in processes:
                print(f"  PID: {pid}")

            return 0

        except Exception as e:
            self.print_error(f"Error listing processes: {e}")
            return 1

    def user_sudo_grant(self, args):
        """Grant sudo privileges to a user"""
        try:
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            # Check if user already has sudo
            if self.user_manager.is_superuser(username):
                self.print_warning(f"User '{username}' already has sudo privileges")
                return 0

            # Check if user has active processes
            processes = self.user_manager.get_user_processes(username)
            is_connected = self.session_monitor.is_user_connected(username)

            if processes or is_connected:
                self.print_warning(f"User '{username}' has active session(s)")
                self.print_warning("WARNING: Group changes only take effect after logout/login")
                self.print_warning("Active sessions will be terminated to apply changes")

                # Ask for confirmation
                if not hasattr(args, 'force') or not args.force:
                    response = input(f"\nContinue and terminate session? (yes/no): ")
                    if response.lower() not in ['yes', 'y']:
                        self.print_info("Cancelled")
                        return 0

            self.print_info(f"Granting sudo privileges to '{username}'...")

            success = self.user_manager.grant_sudo(username, kill_sessions=True)

            if success:
                self.print_success(f"Sudo privileges granted to '{username}'")
                if processes:
                    self.print_info(f"Sessions terminated - user must reconnect to apply changes")
                else:
                    self.print_info(f"User can now execute commands with sudo")
                return 0
            else:
                self.print_error("Failed to grant sudo privileges")
                return 1

        except Exception as e:
            self.print_error(f"Error granting sudo privileges: {e}")
            return 1

    def user_sudo_revoke(self, args):
        """Revoke sudo privileges from a user"""
        try:
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            # Check if user has sudo
            if not self.user_manager.is_superuser(username):
                self.print_warning(f"User '{username}' does not have sudo privileges")
                return 0

            # Check if user has active processes
            processes = self.user_manager.get_user_processes(username)
            is_connected = self.session_monitor.is_user_connected(username)

            if processes or is_connected:
                self.print_warning(f"User '{username}' has active session(s)")
                self.print_warning("WARNING: Group changes only take effect after logout/login")
                self.print_warning("Active sessions will be terminated to apply changes")

                # Ask for confirmation
                if not hasattr(args, 'force') or not args.force:
                    response = input(f"\nContinue and terminate session? (yes/no): ")
                    if response.lower() not in ['yes', 'y']:
                        self.print_info("Cancelled")
                        return 0

            self.print_info(f"Revoking sudo privileges from '{username}'...")

            success = self.user_manager.revoke_sudo(username, kill_sessions=True)

            if success:
                self.print_success(f"Sudo privileges revoked from '{username}'")
                if processes:
                    self.print_info(f"Sessions terminated - user must reconnect to apply changes")
                else:
                    self.print_info(f"User can no longer execute commands with sudo")
                return 0
            else:
                self.print_error("Failed to revoke sudo privileges")
                return 1

        except Exception as e:
            self.print_error(f"Error revoking sudo privileges: {e}")
            return 1

    def user_winege_list(self, args):
        """List available WineGE executables for a user"""
        try:
            import subprocess
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            home_dir = f"/opt/rdp-users/{username}"

            # Check if user is WineGE RemoteApp
            winege_app_path = f"{home_dir}/.winege_app_path"
            if not Path(winege_app_path).exists():
                self.print_error(f"User '{username}' is not a WineGE RemoteApp user")
                return 1

            self.print_header(f"Available Executables for {username}")

            # List executables from WindowsApps
            windows_apps_dir = Path(f"{home_dir}/WindowsApps")
            if windows_apps_dir.exists():
                print(f"\n{self.CYAN}WindowsApps (Portable):{self.RESET}")
                exes = list(windows_apps_dir.glob("*.exe"))
                if exes:
                    for i, exe in enumerate(exes, 1):
                        print(f"  {i}. {exe}")
                else:
                    print("  (none)")

            # List executables from Wine Prefix
            wine_prefix = Path(f"{home_dir}/.wine/drive_c")
            if wine_prefix.exists():
                print(f"\n{self.CYAN}Installed Applications:{self.RESET}")

                # Search in Program Files
                program_files = [
                    wine_prefix / "Program Files",
                    wine_prefix / "Program Files (x86)"
                ]

                installed_exes = []
                for pf in program_files:
                    if pf.exists():
                        for exe in pf.rglob("*.exe"):
                            # Filter out uninstallers and Windows default apps
                            exe_lower = str(exe).lower()
                            if not any(x in exe_lower for x in [
                                'unins', 'uninst', 'windows nt', 'internet explorer',
                                'windows media', 'windows mail', 'windows photo',
                                'wordpad', 'notepad'
                            ]):
                                installed_exes.append(exe)

                if installed_exes:
                    for i, exe in enumerate(installed_exes, 1):
                        print(f"  {i}. {exe}")
                else:
                    print("  (none)")

            # Show current executable
            print(f"\n{self.CYAN}Current Executable:{self.RESET}")
            try:
                with open(winege_app_path, 'r') as f:
                    current = f.read().strip()
                    print(f"  {current}")
            except:
                print("  (none)")

            return 0

        except Exception as e:
            self.print_error(f"Error listing executables: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def user_winege_select(self, args):
        """Interactively select and update WineGE executable for a user"""
        try:
            import subprocess
            username = args.username

            if not self.user_manager.user_exists(username):
                self.print_error(f"User '{username}' does not exist")
                return 1

            home_dir = f"/opt/rdp-users/{username}"

            # Check if user is WineGE RemoteApp
            winege_app_path = f"{home_dir}/.winege_app_path"
            if not Path(winege_app_path).exists():
                self.print_error(f"User '{username}' is not a WineGE RemoteApp user")
                return 1

            # Collect all available executables
            all_exes = []

            # From WindowsApps
            windows_apps_dir = Path(f"{home_dir}/WindowsApps")
            if windows_apps_dir.exists():
                all_exes.extend(windows_apps_dir.glob("*.exe"))

            # From Wine Prefix
            wine_prefix = Path(f"{home_dir}/.wine/drive_c")
            if wine_prefix.exists():
                program_files = [
                    wine_prefix / "Program Files",
                    wine_prefix / "Program Files (x86)"
                ]

                for pf in program_files:
                    if pf.exists():
                        for exe in pf.rglob("*.exe"):
                            exe_lower = str(exe).lower()
                            if not any(x in exe_lower for x in [
                                'unins', 'uninst', 'windows nt', 'internet explorer',
                                'windows media', 'windows mail', 'windows photo',
                                'wordpad', 'notepad'
                            ]):
                                all_exes.append(exe)

            if not all_exes:
                self.print_error("No executables found")
                return 1

            # Display options
            self.print_header(f"Select Executable for {username}")
            print()
            for i, exe in enumerate(all_exes, 1):
                print(f"  {self.CYAN}{i}.{self.RESET} {exe}")
            print()

            # Get user selection
            try:
                choice = input(f"Select number (1-{len(all_exes)}) or 'q' to quit: ").strip()

                if choice.lower() == 'q':
                    self.print_info("Cancelled")
                    return 0

                choice_num = int(choice)
                if choice_num < 1 or choice_num > len(all_exes):
                    self.print_error(f"Invalid selection. Must be between 1 and {len(all_exes)}")
                    return 1

                selected_exe = str(all_exes[choice_num - 1])

            except ValueError:
                self.print_error("Invalid input. Must be a number")
                return 1
            except KeyboardInterrupt:
                print()
                self.print_info("Cancelled")
                return 0

            # Confirm selection
            print()
            self.print_info(f"Selected: {selected_exe}")
            confirm = input("Update executable path? (yes/no): ").strip().lower()

            if confirm not in ['yes', 'y']:
                self.print_info("Cancelled")
                return 0

            # Update using helper script
            helper_script = "/usr/share/rdp-session-manager/helpers/update-winege-exe.sh"
            if not Path(helper_script).exists():
                # Try local path
                helper_script = "./helpers/update-winege-exe.sh"

            if not Path(helper_script).exists():
                self.print_error("Helper script not found. Updating manually...")
                # Fallback to manual update
                try:
                    with open(winege_app_path, 'w') as f:
                        f.write(selected_exe)
                    subprocess.run(['chown', f'{username}:rdp-users', winege_app_path], check=True)
                    self.print_success(f"Executable updated to: {selected_exe}")
                    return 0
                except Exception as e:
                    self.print_error(f"Failed to update: {e}")
                    return 1

            # Use helper script
            # Obter comando de elevação apropriado (pkexec ou sudo)
            _, priv_cmd = get_privilege_command()

            result = subprocess.run(
                priv_cmd + [helper_script, username, selected_exe],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.print_success(f"Executable updated successfully")
                self.print_info(f"New path: {selected_exe}")
                return 0
            else:
                self.print_error(f"Failed to update executable: {result.stderr}")
                return 1

        except Exception as e:
            self.print_error(f"Error selecting executable: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    # ==================== SESSION COMMANDS ====================

    def session_list(self, args):
        """List active RDP sessions"""
        try:
            sessions = self.session_monitor.get_active_sessions()

            if not sessions:
                self.print_info("No active sessions")
                return 0

            if args.format == 'json':
                import json
                sessions_data = [s.to_dict() for s in sessions]
                print(json.dumps(sessions_data, indent=2))
            else:
                self.print_header(f"Active Sessions ({len(sessions)} total)")

                print(f"\n{self.BOLD}{'Username':<20} {'IP Address':<20} {'Port':<8}{self.RESET}")
                print("-" * 50)

                for session in sessions:
                    print(
                        f"{session.username:<20} "
                        f"{session.ip_address:<20} "
                        f"{session.port:<8}"
                    )

            return 0

        except Exception as e:
            self.print_error(f"Error listing sessions: {e}")
            return 1

    def session_info(self, args):
        """Show session information for a user"""
        try:
            username = args.username
            session = self.session_monitor.get_user_session(username)

            if not session:
                self.print_info(f"No active session for user '{username}'")
                return 0

            if args.format == 'json':
                import json
                print(json.dumps(session.to_dict(), indent=2))
            else:
                self.print_header(f"Session Information: {username}")
                print(f"  Username:     {session.username}")
                print(f"  IP Address:   {session.ip_address}")
                print(f"  Port:         {session.port}")
                print(f"  Duration:     {session.get_duration()} seconds")

            return 0

        except Exception as e:
            self.print_error(f"Error getting session info: {e}")
            return 1

    def session_kill(self, args):
        """Kill user session"""
        try:
            username = args.username

            if not self.session_monitor.is_user_connected(username):
                self.print_info(f"User '{username}' is not connected")
                return 0

            # Confirmation
            if not args.force:
                response = input(f"Kill session for '{username}'? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    self.print_info("Cancelled")
                    return 0

            self.print_info(f"Killing session for '{username}'...")

            # Primeiro tenta encerramento gracioso com SIGTERM
            success = self.user_manager.kill_user_processes(username, force=False)

            if not success:
                self.print_error("Failed to kill session")
                return 1

            # Aguarda um momento para os processos encerrarem
            time.sleep(2)

            # Verifica se ainda há processos ativos
            remaining_processes = self.user_manager.get_user_processes(username)

            if remaining_processes:
                self.print_info(f"Some processes still running, forcing termination...")
                # Força o encerramento com SIGKILL
                success = self.user_manager.kill_user_processes(username, force=True)

                if not success:
                    self.print_error("Failed to force kill session")
                    return 1

            self.print_success(f"Session killed for '{username}'")
            return 0

        except Exception as e:
            self.print_error(f"Error killing session: {e}")
            return 1

    # ==================== DESKTOP ENVIRONMENT COMMANDS ====================

    def de_list(self, args):
        """List available desktop environments"""
        try:
            des = self.de_installer.get_available_des()

            if args.format == 'json':
                import json
                print(json.dumps(des, indent=2))
            else:
                self.print_header("Available Desktop Environments")

                print(f"\n{self.BOLD}{'ID':<12} {'Name':<20} {'Size':<10} {'Installed':<15}{self.RESET}")
                print("-" * 60)

                for de in des:
                    installed = self.de_installer.is_de_installed(de['id'])
                    status = f"{self.GREEN}Yes{self.RESET}" if installed else "No"
                    size = f"{de['size_mb']} MB"

                    print(
                        f"{de['id']:<12} "
                        f"{de.get('name', de['id']):<20} "
                        f"{size:<10} "
                        f"{status:<15}"
                    )

            return 0

        except Exception as e:
            self.print_error(f"Error listing desktop environments: {e}")
            return 1

    def de_install(self, args):
        """Install a desktop environment"""
        try:
            de_id = normalize_desktop_id(args.de_id)
            if de_id not in SUPPORTED_DESKTOPS:
                self.print_error(
                    f"Unsupported desktop environment '{args.de_id}'. "
                    f"Options: {', '.join(SUPPORTED_DESKTOPS)}"
                )
                return 1

            # Check if already installed
            if self.de_installer.is_de_installed(de_id):
                self.print_warning(f"Desktop environment '{de_id}' is already installed")
                if not args.force:
                    return 0

            # Check disk space
            has_space, required, available = self.de_installer.check_disk_space(de_id)
            if not has_space:
                self.print_error(f"Insufficient disk space. Required: {required}MB, Available: {available}MB")
                return 1

            self.print_info(f"Installing {de_id.upper()} desktop environment...")

            def progress_callback(progress, message):
                print(f"  {message}")

            success, message = self.de_installer.install_de(
                de_id,
                progress_callback=progress_callback if args.verbose else None
            )

            if success:
                self.print_success(f"Desktop environment '{de_id}' installed successfully")
                return 0
            else:
                self.print_error(f"Failed to install: {message}")
                return 1

        except Exception as e:
            self.print_error(f"Error installing desktop environment: {e}")
            return 1

    def de_check(self, args):
        """Check if desktop environment is installed"""
        try:
            de_id = normalize_desktop_id(args.de_id)
            if de_id not in SUPPORTED_DESKTOPS:
                self.print_error(
                    f"Unsupported desktop environment '{args.de_id}'. "
                    f"Options: {', '.join(SUPPORTED_DESKTOPS)}"
                )
                return 1
            installed = self.de_installer.is_de_installed(de_id)

            if installed:
                self.print_success(f"Desktop environment '{de_id}' is installed")
                return 0
            else:
                self.print_info(f"Desktop environment '{de_id}' is not installed")
                return 1

        except Exception as e:
            self.print_error(f"Error checking desktop environment: {e}")
            return 1

    # ==================== SERVER COMMANDS ====================

    def server_info(self, args):
        """Show server information"""
        try:
            ip = self.session_monitor.get_ip_address()
            port = self.app_config.get_default_rdp_port()
            session_count = self.session_monitor.get_session_count()

            if args.format == 'json':
                import json
                data = {
                    'ip': ip,
                    'port': port,
                    'active_sessions': session_count
                }
                print(json.dumps(data, indent=2))
            else:
                self.print_header("Server Information")
                print(f"  IP Address:       {ip}")
                print(f"  Default RDP Port: {port}")
                print(f"  Active Sessions:  {session_count}")

            return 0

        except Exception as e:
            self.print_error(f"Error getting server info: {e}")
            return 1

    def server_status(self, args):
        """Show a server health snapshot."""
        try:
            import json
            data = self.server_manager.status(self.session_monitor)
            if getattr(args, 'format', 'table') == 'json':
                print(json.dumps(data, indent=2))
            else:
                self.print_header("Server Status")
                for service, active in data['services'].items():
                    print(f"  {service:<14} {'active' if active else 'inactive'}")
                print(f"  Active sessions: {data.get('active_sessions', 0)}")
                print(f"  CPU:             {data['cpu_percent']:.1f}%")
                print(f"  Memory:          {data['memory_percent']:.1f}%")
            return 0 if data['healthy'] else 1

        except Exception as e:
            self.print_error(f"Error checking server status: {e}")
            return 1

    def server_preflight(self, args):
        import json
        data = self.server_manager.preflight()
        print(json.dumps(data, indent=2))
        return 0 if data['ready'] else 1

    def server_plan(self, args):
        import json
        print(json.dumps(self.server_manager.plan(), indent=2))
        return 0

    def server_apply(self, args):
        import json
        from dataclasses import replace
        try:
            settings = self.server_manager.config.load()
            overrides = {}
            for name in (
                'allowed_network', 'max_sessions',
                'disconnected_timeout_seconds', 'idle_timeout_seconds',
                'linux_session_slots', 'windows_session_slots',
            ):
                value = getattr(args, name, None)
                if value is not None:
                    overrides[name] = value
            settings = replace(settings, **overrides)
            assignments = {}
            for user in UserManager(app_config=None).list_users():
                assignments[user.username] = (
                    'windows-standard'
                    if any(p.profile_type == 'winege-remoteapp' for p in user.profiles)
                    else user.default_profile.resource_profile
                )
            print(json.dumps(
                self.server_manager.apply(
                    dry_run=args.dry_run,
                    resource_assignments=assignments,
                    settings=settings,
                ),
                indent=2,
            ))
            return 0
        except Exception as exc:
            self.print_error(f"Failed to apply server profile: {exc}")
            return 1

    def server_benchmark(self, args):
        import json
        print(json.dumps(self.server_manager.benchmark(args.samples), indent=2))
        return 0

    def server_capacity(self, args):
        import json
        profiles = (
            ['windows-standard'] * args.windows
            + ['linux-light'] * args.linux
        )
        data = self.server_manager.capacity(profiles)
        print(json.dumps(data, indent=2))
        return 0 if data['admissible'] else 1

    def server_migrate(self, args):
        import json
        try:
            if not args.apply and not args.rollback:
                print(json.dumps(self.windows_migrator.inventory(args.username), indent=2))
                return 0
            if not args.username:
                self.print_error("--username is required with --apply or --rollback")
                return 2
            data = self.windows_migrator.migrate(args.username, rollback=args.rollback or "")
            print(json.dumps(data, indent=2))
            return 0
        except Exception as exc:
            self.print_error(f"Windows runtime migration failed: {exc}")
            return 1

    # ==================== CONFIG COMMANDS ====================

    def config_get(self, args):
        """Get configuration value"""
        try:
            key = args.key.lower()

            if key == 'port':
                value = self.app_config.get_default_rdp_port()
                print(value)
                return 0
            else:
                self.print_error(f"Unknown configuration key: {key}")
                return 1

        except Exception as e:
            self.print_error(f"Error getting config: {e}")
            return 1

    def config_set(self, args):
        """Set configuration value"""
        try:
            key = args.key.lower()
            value = args.value

            if key == 'port':
                port = int(value)
                success = self.app_config.set_default_rdp_port(port)

                if success:
                    self.print_success(f"Default RDP port set to {port}")
                    return 0
                else:
                    self.print_error("Failed to set port")
                    return 1
            else:
                self.print_error(f"Unknown configuration key: {key}")
                return 1

        except ValueError:
            self.print_error(f"Invalid value for {key}: {value}")
            return 1
        except Exception as e:
            self.print_error(f"Error setting config: {e}")
            return 1

    # ==================== PROFILE COMMANDS ====================

    def profile_list(self, args):
        """List connection profiles for a user"""
        try:
            user = self.user_manager.get_user(args.username)
            if not user:
                self.print_error(f"User '{args.username}' not found")
                return 1

            if getattr(args, 'format', 'table') == 'json':
                import json
                print(json.dumps([p.to_dict() for p in user.profiles], indent=2))
            else:
                self.print_header(f"Connection Sources for '{args.username}'")
                for p in user.profiles:
                    default_str = " (Default)" if p.is_default else ""
                    print(f" • ID: {p.profile_id} | Name: {p.name} | Type: {p.profile_type}{default_str}")
                    if p.profile_type == 'desktop':
                        print(f"   Desktop Environment: {p.desktop_env}")
                    else:
                        print(f"   Command: {p.app_command} {p.app_args}".strip())
            return 0
        except Exception as e:
            self.print_error(f"Error listing profiles: {e}")
            return 1

    def profile_add(self, args):
        """Add a connection profile for a user"""
        try:
            import uuid
            user = self.user_manager.get_user(args.username)
            if not user:
                self.print_error(f"User '{args.username}' not found")
                return 1

            profile_id = str(uuid.uuid4())[:8]
            from core.user_manager import ConnectionProfile
            new_profile = ConnectionProfile(
                profile_id=profile_id,
                name=args.name or "Connection Source",
                profile_type=args.session_type or "desktop",
                desktop_env=args.desktop or "xfce",
                app_command=args.app_command or "",
                app_args=args.app_args or "",
                is_default=args.default
            )

            if args.default:
                for p in user.profiles:
                    p.is_default = False

            user.profiles.append(new_profile)
            if self.user_manager.save_profiles_for_user(args.username, user.profiles):
                self.print_success(f"Added connection profile '{new_profile.name}' (ID: {profile_id}) for {args.username}")
                return 0
            else:
                self.print_error("Failed to save profiles")
                return 1
        except Exception as e:
            self.print_error(f"Error adding profile: {e}")
            return 1

    def profile_remove(self, args):
        """Remove a connection profile for a user"""
        try:
            user = self.user_manager.get_user(args.username)
            if not user:
                self.print_error(f"User '{args.username}' not found")
                return 1

            if len(user.profiles) <= 1:
                self.print_error("Cannot remove the last connection profile of a user")
                return 1

            initial_count = len(user.profiles)
            user.profiles = [p for p in user.profiles if p.profile_id != args.profile_id]

            if len(user.profiles) == initial_count:
                self.print_error(f"Profile ID '{args.profile_id}' not found for user {args.username}")
                return 1

            if not any(p.is_default for p in user.profiles):
                user.profiles[0].is_default = True

            if self.user_manager.save_profiles_for_user(args.username, user.profiles):
                self.print_success(f"Removed connection profile '{args.profile_id}' for {args.username}")
                return 0
            else:
                self.print_error("Failed to save profiles")
                return 1
        except Exception as e:
            self.print_error(f"Error removing profile: {e}")
            return 1

    def profile_set_default(self, args):
        """Set default connection profile for a user"""
        try:
            user = self.user_manager.get_user(args.username)
            if not user:
                self.print_error(f"User '{args.username}' not found")
                return 1

            found = False
            for p in user.profiles:
                if p.profile_id == args.profile_id:
                    p.is_default = True
                    found = True
                else:
                    p.is_default = False

            if not found:
                self.print_error(f"Profile ID '{args.profile_id}' not found for user {args.username}")
                return 1

            if self.user_manager.save_profiles_for_user(args.username, user.profiles):
                self.print_success(f"Profile '{args.profile_id}' set as default for {args.username}")
                return 0
            else:
                self.print_error("Failed to save profiles")
                return 1
        except Exception as e:
            self.print_error(f"Error setting default profile: {e}")
            return 1

    def profile_export(self, args):
        """Export .rdp file for a connection profile"""
        try:
            out_file = args.out or f"{args.username}_{args.profile_id}.rdp"
            if self.user_manager.export_rdp_file(args.username, args.profile_id, out_file):
                self.print_success(f"Exported .rdp file for {args.username} ({args.profile_id}) to {out_file}")
                return 0
            else:
                self.print_error("Failed to export .rdp file")
                return 1
        except Exception as e:
            self.print_error(f"Error exporting profile: {e}")
            return 1

    # ==================== DEPENDENCY COMMANDS ====================

    def deps_check(self, args):
        """Check system dependencies"""
        try:
            all_ok, missing, installed = self.system_deps.check_dependencies()

            if args.format == 'json':
                import json
                data = {
                    'all_ok': all_ok,
                    'missing': missing,
                    'installed': installed
                }
                print(json.dumps(data, indent=2))
            else:
                self.print_header("System Dependencies")

                if installed:
                    print(f"\n{self.GREEN}Installed:{self.RESET}")
                    for dep in installed:
                        print(f"  OK {dep}")

                if missing:
                    print(f"\n{self.RED}Missing:{self.RESET}")
                    for dep in missing:
                        print(f"  X {dep}")

                if all_ok:
                    print(f"\n{self.GREEN}All dependencies are installed{self.RESET}")
                else:
                    print(f"\n{self.YELLOW}Some dependencies are missing{self.RESET}")

            return 0 if all_ok else 1

        except Exception as e:
            self.print_error(f"Error checking dependencies: {e}")
            return 1

    def deps_install(self, args):
        """Install system dependency"""
        try:
            package = args.package

            self.print_info(f"Installing {package}...")

            def progress_callback(progress, message):
                print(f"  {message}")

            success, message = self.system_deps.install_package(
                package,
                progress_callback=progress_callback if args.verbose else None
            )

            if success:
                self.print_success(f"Package '{package}' installed successfully")
                return 0
            else:
                self.print_error(f"Failed to install: {message}")
                return 1

        except Exception as e:
            self.print_error(f"Error installing package: {e}")
            return 1

    # ==================== MAIN ====================

    def run(self, argv=None):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            prog='rdpsm',
            description='RDP Session Manager - Command Line Interface',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument('-v', '--verbose', action='store_true',
                          help='Verbose output')
        parser.add_argument('--version', action='version', version=f'RDPSM {__version__}')

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # User commands
        user_parser = subparsers.add_parser('user', help='User management')
        user_subparsers = user_parser.add_subparsers(dest='subcommand')

        # user create
        user_create = user_subparsers.add_parser('create', help='Create a new user')
        user_create.add_argument('username', help='Username')
        user_create.add_argument('-f', '--fullname', help='Full name')
        user_create.add_argument('-d', '--desktop', default='xfce',
                                help='Desktop environment (default: xfce, used for desktop sessions)')
        user_create.add_argument('-p', '--password', help='Password (will prompt if not provided)')
        user_create.add_argument('-s', '--session-type', choices=['desktop', 'remoteapp', 'winege-remoteapp'], default='desktop',
                                help='Session type: desktop (full DE), remoteapp (single app), or winege-remoteapp (Windows app via WineGE)')
        user_create.add_argument('--app-command', help='Application command for RemoteApp or .exe path for Windows RemoteApp')
        user_create.add_argument('--app-args', default='', help='Application arguments for RemoteApp/WineGE (e.g., --private-window)')
        user_create.set_defaults(func=self.user_create)

        # user delete
        user_delete = user_subparsers.add_parser('delete', help='Delete a user')
        user_delete.add_argument('username', help='Username')
        user_delete.add_argument('--force', action='store_true',
                                help='Skip confirmation')
        user_delete.set_defaults(func=self.user_delete)

        # user list
        user_list = user_subparsers.add_parser('list', help='List all users')
        user_list.add_argument('--format', choices=['table', 'json'], default='table',
                              help='Output format')
        user_list.set_defaults(func=self.user_list)

        # user info
        user_info = user_subparsers.add_parser('info', help='Show user information')
        user_info.add_argument('username', help='Username')
        user_info.add_argument('--format', choices=['table', 'json'], default='table',
                              help='Output format')
        user_info.set_defaults(func=self.user_info)

        # user enable
        user_enable = user_subparsers.add_parser('enable', help='Enable a user')
        user_enable.add_argument('username', help='Username')
        user_enable.set_defaults(func=self.user_enable)

        # user disable
        user_disable = user_subparsers.add_parser('disable', help='Disable a user')
        user_disable.add_argument('username', help='Username')
        user_disable.set_defaults(func=self.user_disable)

        # user password
        user_password = user_subparsers.add_parser('password', help='Change user password')
        user_password.add_argument('username', help='Username')
        user_password.add_argument('-p', '--password', help='New password (will prompt if not provided)')
        user_password.set_defaults(func=self.user_password)

        # user processes
        user_processes = user_subparsers.add_parser('processes', help='List user processes')
        user_processes.add_argument('username', help='Username')
        user_processes.set_defaults(func=self.user_processes)

        # user sudo (sub-subcommand)
        user_sudo = user_subparsers.add_parser('sudo', help='Manage sudo privileges')
        user_sudo_subparsers = user_sudo.add_subparsers(dest='sudo_action')

        # user sudo grant
        user_sudo_grant = user_sudo_subparsers.add_parser('grant', help='Grant sudo privileges to user')
        user_sudo_grant.add_argument('username', help='Username')
        user_sudo_grant.add_argument('--force', action='store_true',
                                     help='Skip confirmation if user has active session')
        user_sudo_grant.set_defaults(func=self.user_sudo_grant)

        # user sudo revoke
        user_sudo_revoke = user_sudo_subparsers.add_parser('revoke', help='Revoke sudo privileges from user')
        user_sudo_revoke.add_argument('username', help='Username')
        user_sudo_revoke.add_argument('--force', action='store_true',
                                      help='Skip confirmation if user has active session')
        user_sudo_revoke.set_defaults(func=self.user_sudo_revoke)

        # user winege (sub-subcommand)
        user_winege = user_subparsers.add_parser('winege', help='Manage Windows RemoteApp executables (legacy command name)')
        user_winege_subparsers = user_winege.add_subparsers(dest='winege_action')

        # user winege list
        user_winege_list = user_winege_subparsers.add_parser('list', help='List available executables for WineGE user')
        user_winege_list.add_argument('username', help='Username')
        user_winege_list.set_defaults(func=self.user_winege_list)

        # user winege select
        user_winege_select = user_winege_subparsers.add_parser('select', help='Interactively select and update executable')
        user_winege_select.add_argument('username', help='Username')
        user_winege_select.set_defaults(func=self.user_winege_select)

        # Session commands
        session_parser = subparsers.add_parser('session', help='Session management')
        session_subparsers = session_parser.add_subparsers(dest='subcommand')

        # session list
        session_list = session_subparsers.add_parser('list', help='List active sessions')
        session_list.add_argument('--format', choices=['table', 'json'], default='table',
                                 help='Output format')
        session_list.set_defaults(func=self.session_list)

        # session info
        session_info = session_subparsers.add_parser('info', help='Show session information')
        session_info.add_argument('username', help='Username')
        session_info.add_argument('--format', choices=['table', 'json'], default='table',
                                 help='Output format')
        session_info.set_defaults(func=self.session_info)

        # session kill
        session_kill = session_subparsers.add_parser('kill', help='Kill user session')
        session_kill.add_argument('username', help='Username')
        session_kill.add_argument('--force', action='store_true',
                                 help='Skip confirmation')
        session_kill.set_defaults(func=self.session_kill)

        # Desktop Environment commands
        de_parser = subparsers.add_parser('de', help='Desktop environment management')
        de_subparsers = de_parser.add_subparsers(dest='subcommand')

        # de list
        de_list = de_subparsers.add_parser('list', help='List available desktop environments')
        de_list.add_argument('--format', choices=['table', 'json'], default='table',
                            help='Output format')
        de_list.set_defaults(func=self.de_list)

        # de install
        de_install = de_subparsers.add_parser('install', help='Install desktop environment')
        de_install.add_argument('de_id', help='Desktop environment ID (xfce, gnome, kde)')
        de_install.add_argument('--force', action='store_true',
                               help='Reinstall if already installed')
        de_install.set_defaults(func=self.de_install)

        # de check
        de_check = de_subparsers.add_parser('check', help='Check if DE is installed')
        de_check.add_argument('de_id', help='Desktop environment ID')
        de_check.set_defaults(func=self.de_check)

        # Server commands
        server_parser = subparsers.add_parser('server', help='Server information')
        server_subparsers = server_parser.add_subparsers(dest='subcommand')

        # server info
        server_info = server_subparsers.add_parser('info', help='Show server information')
        server_info.add_argument('--format', choices=['table', 'json'], default='table',
                                help='Output format')
        server_info.set_defaults(func=self.server_info)

        # server status
        server_status = server_subparsers.add_parser('status', help='Check xrdp server status')
        server_status.add_argument('--format', choices=['table', 'json'], default='table')
        server_status.set_defaults(func=self.server_status)

        server_preflight = server_subparsers.add_parser('preflight', help='Validate production readiness')
        server_preflight.set_defaults(func=self.server_preflight)

        server_plan = server_subparsers.add_parser('plan', help='Show production profile changes')
        server_plan.set_defaults(func=self.server_plan)

        server_apply = server_subparsers.add_parser('apply', help='Apply the production server profile')
        server_apply.add_argument('--dry-run', action='store_true')
        server_apply.add_argument('--allowed-network', help='Private/VPN CIDR allowed to reach RDP')
        server_apply.add_argument('--max-sessions', type=int)
        server_apply.add_argument('--disconnected-timeout-seconds', type=int)
        server_apply.add_argument('--idle-timeout-seconds', type=int)
        server_apply.add_argument('--linux-session-slots', type=int)
        server_apply.add_argument('--windows-session-slots', type=int)
        server_apply.set_defaults(func=self.server_apply)

        server_benchmark = server_subparsers.add_parser('benchmark', help='Measure status collection overhead')
        server_benchmark.add_argument('--samples', type=int, default=5)
        server_benchmark.set_defaults(func=self.server_benchmark)

        server_capacity = server_subparsers.add_parser('capacity', help='Validate a proposed session mix')
        server_capacity.add_argument('--linux', type=int, default=0)
        server_capacity.add_argument('--windows', type=int, default=0)
        server_capacity.set_defaults(func=self.server_capacity)

        server_migrate = server_subparsers.add_parser('migrate', help='Inventory or migrate legacy WineGE users')
        server_migrate.add_argument('--username')
        server_migrate.add_argument('--apply', action='store_true')
        server_migrate.add_argument('--rollback', metavar='BACKUP_DIR')
        server_migrate.set_defaults(func=self.server_migrate)

        # Config commands
        config_parser = subparsers.add_parser('config', help='Configuration management')
        config_subparsers = config_parser.add_subparsers(dest='subcommand')

        # config get
        config_get = config_subparsers.add_parser('get', help='Get configuration value')
        config_get.add_argument('key', help='Configuration key (port)')
        config_get.set_defaults(func=self.config_get)

        # config set
        config_set = config_subparsers.add_parser('set', help='Set configuration value')
        config_set.add_argument('key', help='Configuration key (port)')
        config_set.add_argument('value', help='Value')
        config_set.set_defaults(func=self.config_set)

        # Profile commands
        profile_parser = subparsers.add_parser('profile', help='Connection profile management')
        profile_subparsers = profile_parser.add_subparsers(dest='subcommand')

        # profile list
        p_list = profile_subparsers.add_parser('list', help='List connection profiles for a user')
        p_list.add_argument('username', help='Username')
        p_list.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
        p_list.set_defaults(func=self.profile_list)

        # profile add
        p_add = profile_subparsers.add_parser('add', help='Add a connection profile')
        p_add.add_argument('username', help='Username')
        p_add.add_argument('-n', '--name', required=True, help='Display name for connection source')
        p_add.add_argument('-s', '--session-type', choices=['desktop', 'remoteapp', 'winege-remoteapp'], default='desktop', help='Session type')
        p_add.add_argument('-d', '--desktop', default='xfce', help='Desktop environment')
        p_add.add_argument('--app-command', default='', help='App command or .exe path')
        p_add.add_argument('--app-args', default='', help='App arguments')
        p_add.add_argument('--default', action='store_true', help='Set as default connection source')
        p_add.set_defaults(func=self.profile_add)

        # profile export
        p_exp = profile_subparsers.add_parser('export', help='Export .rdp file for a connection profile')
        p_exp.add_argument('username', help='Username')
        p_exp.add_argument('profile_id', help='Profile ID')
        p_exp.add_argument('-o', '--out', help='Output .rdp file path')
        p_exp.set_defaults(func=self.profile_export)

        # profile remove
        p_rem = profile_subparsers.add_parser('remove', help='Remove a connection profile')
        p_rem.add_argument('username', help='Username')
        p_rem.add_argument('profile_id', help='Profile ID')
        p_rem.set_defaults(func=self.profile_remove)

        # profile set-default
        p_def = profile_subparsers.add_parser('set-default', help='Set default connection profile')
        p_def.add_argument('username', help='Username')
        p_def.add_argument('profile_id', help='Profile ID')
        p_def.set_defaults(func=self.profile_set_default)

        # Parse arguments
        args = parser.parse_args(argv)

        # Setup logging
        file_logging = args.command != 'server'
        if args.verbose:
            setup_logger(log_level=logging.DEBUG, file_logging=file_logging)
        else:
            setup_logger(log_level=logging.WARNING, file_logging=file_logging)

        # Execute command
        if hasattr(args, 'func'):
            return args.func(args)
        else:
            parser.print_help()
            return 0


def main():
    """Entry point for CLI"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
