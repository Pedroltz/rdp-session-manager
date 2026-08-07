#!/usr/bin/env python3
"""
Tests for UserManager module
"""

import unittest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.user_manager import ConnectionProfile, UserManager, RDPUser


class TestUserManager(unittest.TestCase):
    """Test UserManager class"""

    def setUp(self):
        """Setup test fixtures"""
        # UserManager agora recebe app_config como primeiro parâmetro, rdp_users_home como segundo
        self.user_manager = UserManager(app_config=None, rdp_users_home="/tmp/test-rdp-users")

    def test_rdp_user_to_dict(self):
        """Test RDPUser to_dict method"""
        user = RDPUser(
            username='testuser',
            uid=5000,
            home_dir='/tmp/testuser',
            desktop_env='xfce',
            rdp_port=3389,
            active=True
        )

        user_dict = user.to_dict()

        self.assertEqual(user_dict['username'], 'testuser')
        self.assertEqual(user_dict['uid'], 5000)
        self.assertTrue(user_dict['active'])
        self.assertTrue(user_dict['enabled'])
        self.assertFalse(user_dict['is_superuser'])

    def test_rdp_user_to_dict_full(self):
        """Test RDPUser to_dict with all fields"""
        user = RDPUser(
            username='adminuser',
            uid=5001,
            home_dir='/tmp/adminuser',
            desktop_env='gnome',
            rdp_port=3390,
            active=True,
            enabled=False,
            is_superuser=True
        )

        user_dict = user.to_dict()

        self.assertEqual(user_dict['username'], 'adminuser')
        self.assertEqual(user_dict['uid'], 5001)
        self.assertEqual(user_dict['desktop_env'], 'gnome')
        self.assertEqual(user_dict['rdp_port'], 3390)
        self.assertTrue(user_dict['active'])
        self.assertFalse(user_dict['enabled'])
        self.assertTrue(user_dict['is_superuser'])

    def test_rdp_user_from_dict(self):
        """Test RDPUser from_dict method"""
        data = {
            'username': 'testuser',
            'uid': 5000,
            'home_dir': '/tmp/testuser',
            'desktop_env': 'xfce',
            'rdp_port': 3389,
            'active': False
        }

        user = RDPUser.from_dict(data)

        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.uid, 5000)
        self.assertFalse(user.active)

    def test_rdp_user_from_dict_full(self):
        """Test RDPUser from_dict with all fields"""
        data = {
            'username': 'poweruser',
            'uid': 5002,
            'home_dir': '/opt/rdp-users/poweruser',
            'desktop_env': 'kde',
            'rdp_port': 3391,
            'active': True,
            'enabled': True,
            'is_superuser': False
        }

        user = RDPUser.from_dict(data)

        self.assertEqual(user.username, 'poweruser')
        self.assertEqual(user.uid, 5002)
        self.assertEqual(user.home_dir, '/opt/rdp-users/poweruser')
        self.assertEqual(user.desktop_env, 'kde')
        self.assertEqual(user.rdp_port, 3391)
        self.assertTrue(user.active)
        self.assertTrue(user.enabled)
        self.assertFalse(user.is_superuser)

    def test_validate_username(self):
        """Test username validation"""
        self.assertTrue(self.user_manager._validate_username('validuser'))
        self.assertTrue(self.user_manager._validate_username('user123'))
        self.assertFalse(self.user_manager._validate_username('123user'))
        self.assertFalse(self.user_manager._validate_username('User'))
        self.assertFalse(self.user_manager._validate_username('ab'))

    def test_get_next_uid(self):
        """Test UID generation"""
        uid = self.user_manager._get_next_uid()
        self.assertGreaterEqual(uid, UserManager.RDP_UID_START)

    def test_get_next_rdp_port(self):
        """Test RDP port generation"""
        # _detect_rdp_port agora recebe UID e retorna a porta baseada na config global
        port = self.user_manager._detect_rdp_port(5001)
        self.assertEqual(port, 3389)  # Deve retornar a porta padrão

    def test_detects_session_from_current_dispatcher_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".xsession").write_text(
                'exec /usr/bin/python3 "/opt/rdp-users/rdpsm-session.py" "${1:-}"\n',
                encoding="utf-8",
            )
            (home / ".rdp_profiles.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "profiles": [
                            {
                                "profile_type": "winege-remoteapp",
                                "app_command": "/opt/rdp-users/note/WindowsApps/nppp.exe",
                                "app_args": "",
                                "is_default": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            session = self.user_manager._detect_session_info(str(home))

        self.assertEqual(
            session,
            (
                "winege-remoteapp",
                "/opt/rdp-users/note/WindowsApps/nppp.exe",
                "",
            ),
        )

    def test_rdp_user_defaults(self):
        """Test RDPUser default values"""
        user = RDPUser(
            username='defaultuser',
            uid=5003,
            home_dir='/tmp/defaultuser',
            desktop_env='lxde',
            rdp_port=3389
        )

        # Verificar defaults
        self.assertFalse(user.active)
        self.assertTrue(user.enabled)
        self.assertFalse(user.is_superuser)

    def test_rdp_user_serialization_roundtrip(self):
        """Test RDPUser serialization and deserialization"""
        original_user = RDPUser(
            username='roundtripuser',
            uid=5004,
            home_dir='/opt/rdp-users/roundtripuser',
            desktop_env='mate',
            rdp_port=3392,
            active=True,
            enabled=False,
            is_superuser=True
        )

        # Converter para dict e de volta
        user_dict = original_user.to_dict()
        restored_user = RDPUser.from_dict(user_dict)

        # Verificar que todos os valores foram preservados
        self.assertEqual(restored_user.username, original_user.username)
        self.assertEqual(restored_user.uid, original_user.uid)
        self.assertEqual(restored_user.home_dir, original_user.home_dir)
        self.assertEqual(restored_user.desktop_env, original_user.desktop_env)
        self.assertEqual(restored_user.rdp_port, original_user.rdp_port)
        self.assertEqual(restored_user.active, original_user.active)
        self.assertEqual(restored_user.enabled, original_user.enabled)
        self.assertEqual(restored_user.is_superuser, original_user.is_superuser)

    @patch('grp.getgrnam')
    def test_ensure_rdp_group_exists(self, mock_getgrnam):
        """Test that RDP group check works when group exists"""
        # Simular grupo existente
        mock_group = Mock()
        mock_group.gr_gid = 1001
        mock_getgrnam.return_value = mock_group

        gid = self.user_manager._ensure_rdp_group()

        self.assertEqual(gid, 1001)
        mock_getgrnam.assert_called_once_with('rdp-users')

    @patch('grp.getgrnam')
    def test_ensure_rdp_group_not_exists(self, mock_getgrnam):
        """Test that RDP group check fails when group doesn't exist"""
        # Simular grupo não existente
        mock_getgrnam.side_effect = KeyError('rdp-users')

        gid = self.user_manager._ensure_rdp_group()

        self.assertEqual(gid, -1)

    def test_validate_username_edge_cases(self):
        """Test username validation edge cases"""
        # Caso limite: 3 caracteres (mínimo)
        self.assertTrue(self.user_manager._validate_username('abc'))

        # Caso limite: 32 caracteres (máximo)
        self.assertTrue(self.user_manager._validate_username('a' * 32))

        # Muito longo: 33 caracteres
        self.assertFalse(self.user_manager._validate_username('a' * 33))

        # Caracteres especiais válidos
        self.assertTrue(self.user_manager._validate_username('user-name'))
        self.assertTrue(self.user_manager._validate_username('user_name'))

        # Caracteres especiais inválidos
        self.assertFalse(self.user_manager._validate_username('user@name'))
        self.assertFalse(self.user_manager._validate_username('user.name'))

    @patch('core.user_manager.get_privilege_command')
    @patch('core.user_manager.subprocess.run')
    def test_create_system_user_uses_one_elevation_and_password_stdin(
        self, run, privilege
    ):
        privilege.return_value = ('pkexec', ['pkexec', '--user', 'root'])
        run.return_value = Mock(returncode=0, stdout='OK\n', stderr='')
        profile = ConnectionProfile(
            'default',
            'Windows App',
            'winege-remoteapp',
            app_command='/tmp/example.exe',
            is_default=True,
        )

        created = self.user_manager._create_system_user(
            username='rdptest',
            password='a password:with symbols!',
            uid=5000,
            home_dir='/opt/rdp-users/rdptest',
            full_name='RDP Test',
            desktop_env='xfce',
            session_type='winege-remoteapp',
            app_command='/tmp/example.exe',
            profiles=[profile],
        )

        self.assertTrue(created)
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ['pkexec', '--user', 'root'])
        self.assertNotIn('a password:with symbols!', command)
        self.assertEqual(
            run.call_args.kwargs['input'],
            'a password:with symbols!\n',
        )

    @patch('core.user_manager.get_privilege_command')
    def test_unreadable_profile_does_not_request_elevation(self, privilege):
        with tempfile.TemporaryDirectory() as directory:
            profile_file = Path(directory) / '.rdp_profiles.json'
            profile_file.write_text('{}', encoding='utf-8')
            profile_file.chmod(0)
            try:
                profiles = self.user_manager.load_profiles_for_user(
                    directory,
                    default_session_type='desktop',
                    default_de='xfce',
                )
            finally:
                profile_file.chmod(0o600)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].profile_type, 'desktop')
        privilege.assert_not_called()

    def test_detects_windows_runtime_when_profile_is_unreadable(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.xsession').write_text(
                'exec /usr/bin/python3 /opt/rdp-users/rdpsm-session.py\n',
                encoding='utf-8',
            )
            (home / '.xinitrc').symlink_to(home / '.xsession')
            profile = home / '.rdp_profiles.json'
            profile.write_text('{}', encoding='utf-8')
            profile.chmod(0)
            (home / '.windows_runtime.json').write_text(
                '{}', encoding='utf-8'
            )
            (home / '.winege_app_path').write_text(
                '/opt/rdp-users/test/WindowsApps/example.exe\n',
                encoding='utf-8',
            )
            try:
                detected = self.user_manager._detect_session_info(directory)
            finally:
                profile.chmod(0o600)

        self.assertEqual(
            detected,
            (
                'winege-remoteapp',
                '/opt/rdp-users/test/WindowsApps/example.exe',
                '',
            ),
        )

    def test_executable_listing_keeps_notepad_plus_plus_and_hides_wine_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'rdptest'
            windows_apps = home / 'WindowsApps'
            program_files = home / '.wine' / 'drive_c' / 'Program Files'
            notepad_plus = program_files / 'Notepad++' / 'notepad++.exe'
            updater = program_files / 'Notepad++' / 'updater' / 'GUP.exe'
            uninstaller = program_files / 'Notepad++' / 'uninstall.exe'
            wine_notepad = (
                home / '.wine' / 'drive_c' / 'windows' / 'system32' / 'notepad.exe'
            )
            installer = windows_apps / 'npp.Installer.x64.exe'
            for executable in (notepad_plus, updater, uninstaller, wine_notepad, installer):
                executable.parent.mkdir(parents=True, exist_ok=True)
                executable.touch()

            manager = UserManager(app_config=None, rdp_users_home=Path(directory))
            manager.user_exists = Mock(return_value=True)
            listed = manager.list_user_executables('rdptest')

        paths = {path for _, path in listed}
        self.assertIn(str(notepad_plus), paths)
        self.assertIn(str(installer), paths)
        self.assertNotIn(str(updater), paths)
        self.assertNotIn(str(uninstaller), paths)
        self.assertNotIn(str(wine_notepad), paths)

    @patch('core.user_manager.get_privilege_command')
    @patch('core.user_manager.subprocess.run')
    def test_repair_user_uses_one_elevation_and_password_stdin(
        self, run, privilege
    ):
        profile = ConnectionProfile(
            'default',
            'Windows App',
            'winege-remoteapp',
            app_command='/opt/rdp-users/rdptest/WindowsApps/example.exe',
            is_default=True,
        )
        user = RDPUser(
            username='rdptest',
            uid=5000,
            home_dir='/opt/rdp-users/rdptest',
            session_type='winege-remoteapp',
            app_command=profile.app_command,
            profiles=[profile],
        )
        self.user_manager.diagnose_user = Mock(return_value={
            'exists': True,
            'managed': True,
            'active': False,
            'issues': [],
        })
        self.user_manager.get_user = Mock(return_value=user)
        privilege.return_value = ('sudo', ['sudo'])
        run.return_value = Mock(returncode=0, stdout='OK repaired\n', stderr='')

        success, _ = self.user_manager.repair_user(
            'rdptest', 'new password', profiles=[profile]
        )

        self.assertTrue(success)
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[0], 'sudo')
        self.assertNotIn('new password', command)
        self.assertEqual(run.call_args.kwargs['input'], 'new password\n')

    @patch('core.user_manager.get_privilege_command')
    @patch('core.user_manager.subprocess.run')
    def test_lock_user_kills_sessions(self, mock_run, mock_privilege):
        """Test lock_user calls toggle script and kills user processes"""
        self.user_manager.user_exists = Mock(return_value=True)
        self.user_manager.kill_user_processes = Mock(return_value=True)
        self.user_manager._save_states_cache = Mock()
        mock_privilege.return_value = ('sudo', ['sudo'])
        mock_run.return_value = Mock(returncode=0, stdout='OK locked', stderr='')

        success = self.user_manager.lock_user('rdptest', kill_sessions=True)

        self.assertTrue(success)
        mock_run.assert_called_once()
        command = mock_run.call_args.args[0]
        self.assertIn('toggle-user-lock.sh', command[1])
        self.assertEqual(command[2], 'rdptest')
        self.assertEqual(command[3], 'lock')
        self.user_manager.kill_user_processes.assert_called_once_with('rdptest', force=False)
        self.assertFalse(UserManager._user_states_cache.get('rdptest'))

    @patch('core.user_manager.get_privilege_command')
    @patch('core.user_manager.subprocess.run')
    def test_unlock_user(self, mock_run, mock_privilege):
        """Test unlock_user calls toggle script for unlock"""
        self.user_manager.user_exists = Mock(return_value=True)
        self.user_manager._save_states_cache = Mock()
        mock_privilege.return_value = ('sudo', ['sudo'])
        mock_run.return_value = Mock(returncode=0, stdout='OK unlocked', stderr='')

        success = self.user_manager.unlock_user('rdptest')

        self.assertTrue(success)
        mock_run.assert_called_once()
        command = mock_run.call_args.args[0]
        self.assertIn('toggle-user-lock.sh', command[1])
        self.assertEqual(command[2], 'rdptest')
        self.assertEqual(command[3], 'unlock')
        self.assertTrue(UserManager._user_states_cache.get('rdptest'))


if __name__ == '__main__':
    unittest.main()
