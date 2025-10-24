#!/usr/bin/env python3
"""
RDP Session Manager - Command Line Interface
"""

import sys
import argparse
import logging
from typing import Optional
from pathlib import Path

from core.user_manager import UserManager
from core.session_monitor import SessionMonitor
from core.de_installer import DEInstaller
from core.system_deps import SystemDependencies
from core.config import AppConfig
from utils.logger import setup_logger

logger = logging.getLogger(__name__)


class CLI:
    """Command Line Interface for RDP Session Manager"""

    def __init__(self):
        self.app_config = AppConfig()
        self.user_manager = UserManager(self.app_config)
        self.session_monitor = SessionMonitor()
        self.de_installer = DEInstaller()
        self.system_deps = SystemDependencies()

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

    def print_success(self, message: str):
        """Print success message"""
        print(f"{self.GREEN}✓{self.RESET} {message}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"{self.RED}✗{self.RESET} {message}", file=sys.stderr)

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
            desktop_env = args.desktop or "xfce"

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

            # Check if Desktop Environment is installed
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

            user = self.user_manager.create_user(
                username=username,
                password=password,
                desktop_env=desktop_env,
                full_name=full_name,
                log_callback=lambda msg: print(f"  {msg}") if args.verbose else None
            )

            if user:
                self.print_success(f"User '{username}' created successfully")
                self.print_info(f"UID: {user.uid}")
                self.print_info(f"Home: {user.home_dir}")
                self.print_info(f"RDP Port: {user.rdp_port}")
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
                print(f"  Desktop:      {user.desktop_env.upper()}")
                print(f"  RDP Port:     {user.rdp_port}")
                print(f"  Status:       {'Enabled' if user.enabled else 'Disabled'}")

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
                self.print_warning("⚠ IMPORTANT: Group changes only take effect after logout/login")
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
                self.print_warning("⚠ IMPORTANT: Group changes only take effect after logout/login")
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

            success = self.session_monitor.kill_user_session(username)

            if success:
                self.print_success(f"Session killed for '{username}'")
                return 0
            else:
                self.print_error("Failed to kill session")
                return 1

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
                    size = de.get('size', 'N/A')

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
            de_id = args.de_id

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
            de_id = args.de_id
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
        """Check xrdp server status"""
        try:
            xrdp_ready = self.system_deps.is_xrdp_ready()

            if xrdp_ready:
                self.print_success("xrdp server is installed and running")
                return 0
            else:
                self.print_warning("xrdp server is not installed or not running")
                return 1

        except Exception as e:
            self.print_error(f"Error checking server status: {e}")
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
                        print(f"  ✓ {dep}")

                if missing:
                    print(f"\n{self.RED}Missing:{self.RESET}")
                    for dep in missing:
                        print(f"  ✗ {dep}")

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
        parser.add_argument('--version', action='version', version='RDPSM 0.2.1')

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # User commands
        user_parser = subparsers.add_parser('user', help='User management')
        user_subparsers = user_parser.add_subparsers(dest='subcommand')

        # user create
        user_create = user_subparsers.add_parser('create', help='Create a new user')
        user_create.add_argument('username', help='Username')
        user_create.add_argument('-f', '--fullname', help='Full name')
        user_create.add_argument('-d', '--desktop', default='xfce',
                                help='Desktop environment (default: xfce)')
        user_create.add_argument('-p', '--password', help='Password (will prompt if not provided)')
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
        de_install.add_argument('de_id', help='Desktop environment ID (xfce, gnome, etc.)')
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
        server_status.set_defaults(func=self.server_status)

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

        # Dependencies commands
        deps_parser = subparsers.add_parser('deps', help='Dependency management')
        deps_subparsers = deps_parser.add_subparsers(dest='subcommand')

        # deps check
        deps_check = deps_subparsers.add_parser('check', help='Check system dependencies')
        deps_check.add_argument('--format', choices=['table', 'json'], default='table',
                               help='Output format')
        deps_check.set_defaults(func=self.deps_check)

        # deps install
        deps_install = deps_subparsers.add_parser('install', help='Install dependency')
        deps_install.add_argument('package', help='Package name (xrdp, freerdp)')
        deps_install.set_defaults(func=self.deps_install)

        # Parse arguments
        args = parser.parse_args(argv)

        # Setup logging
        if args.verbose:
            setup_logger(log_level=logging.DEBUG)
        else:
            setup_logger(log_level=logging.WARNING)

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
