#!/usr/bin/env python3
"""
PolicyKit Helper Script
Executa operações privilegiadas via PolicyKit
"""

import sys
import json
import os
import subprocess
import pwd
import grp
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_rdp_group():
    """Cria o grupo rdp-users se não existir"""
    try:
        grp.getgrnam('rdp-users')
        return True
    except KeyError:
        result = subprocess.run(
            ['groupadd', 'rdp-users'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0


def create_user(args):
    """Cria um novo usuário RDP"""
    username = args['username']
    password = args['password']
    uid = args['uid']
    home_dir = args['home_dir']
    full_name = args.get('full_name', '')

    try:
        # Criar grupo rdp-users se não existir
        if not create_rdp_group():
            return {'success': False, 'error': 'Failed to create rdp-users group'}

        # Criar diretório base se não existir
        base_dir = Path(home_dir).parent
        base_dir.mkdir(parents=True, exist_ok=True)

        # Criar usuário
        cmd = [
            'useradd',
            '-u', str(uid),
            '-d', home_dir,
            '-m',  # Criar home directory
            '-g', 'rdp-users',
            '-s', '/bin/bash',
        ]

        if full_name:
            cmd.extend(['-c', full_name])

        cmd.append(username)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {'success': False, 'error': result.stderr}

        # Definir senha
        proc = subprocess.Popen(
            ['chpasswd'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        proc.communicate(input=f"{username}:{password}")

        if proc.returncode != 0:
            return {'success': False, 'error': 'Failed to set password'}

        logger.info(f"User {username} created successfully")
        return {'success': True, 'username': username, 'uid': uid, 'home_dir': home_dir}

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return {'success': False, 'error': str(e)}


def delete_user(args):
    """Remove um usuário RDP"""
    username = args['username']
    remove_home = args.get('remove_home', True)

    try:
        # Verificar se usuário existe
        pwd.getpwnam(username)

        # Remover usuário
        cmd = ['userdel']

        if remove_home:
            cmd.append('-r')

        cmd.append(username)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {'success': False, 'error': result.stderr}

        logger.info(f"User {username} deleted successfully")
        return {'success': True, 'username': username}

    except KeyError:
        return {'success': False, 'error': f'User {username} not found'}
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return {'success': False, 'error': str(e)}


def modify_user(args):
    """Modifica um usuário RDP"""
    username = args['username']

    try:
        # Verificar se usuário existe
        pwd.getpwnam(username)

        # Modificar senha se fornecida
        if 'new_password' in args:
            proc = subprocess.Popen(
                ['chpasswd'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            proc.communicate(input=f"{username}:{args['new_password']}")

            if proc.returncode != 0:
                return {'success': False, 'error': 'Failed to change password'}

        logger.info(f"User {username} modified successfully")
        return {'success': True, 'username': username}

    except KeyError:
        return {'success': False, 'error': f'User {username} not found'}
    except Exception as e:
        logger.error(f"Error modifying user: {e}")
        return {'success': False, 'error': str(e)}


def install_desktop(args):
    """Instala um ambiente desktop"""
    de_packages = args.get('packages', [])

    try:
        # Atualizar cache
        subprocess.run(['apt-get', 'update'], check=True, capture_output=True)

        # Instalar pacotes
        cmd = ['apt-get', 'install', '-y'] + de_packages

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {'success': False, 'error': result.stderr}

        logger.info(f"Desktop environment installed: {de_packages}")
        return {'success': True, 'packages': de_packages}

    except Exception as e:
        logger.error(f"Error installing desktop: {e}")
        return {'success': False, 'error': str(e)}


def manage_sessions(args):
    """Gerencia sessões RDP"""
    action = args.get('session_action')
    username = args.get('username')

    try:
        if action == 'kill':
            # Matar processos do usuário
            subprocess.run(['pkill', '-u', username], capture_output=True)
            return {'success': True, 'action': 'killed', 'username': username}

        return {'success': False, 'error': f'Unknown action: {action}'}

    except Exception as e:
        logger.error(f"Error managing sessions: {e}")
        return {'success': False, 'error': str(e)}


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': 'No arguments provided'}))
        sys.exit(1)

    try:
        # Parse arguments
        args = json.loads(sys.argv[1])
        action = args.get('action')

        # Execute action
        if action == 'create-user':
            result = create_user(args)
        elif action == 'delete-user':
            result = delete_user(args)
        elif action == 'modify-user':
            result = modify_user(args)
        elif action == 'install-desktop':
            result = install_desktop(args)
        elif action == 'manage-sessions':
            result = manage_sessions(args)
        else:
            result = {'success': False, 'error': f'Unknown action: {action}'}

        # Output result
        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(json.dumps({'success': False, 'error': f'Invalid JSON: {e}'}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
