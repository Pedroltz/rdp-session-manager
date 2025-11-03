#!/usr/bin/env python3
"""
Módulo de gerenciamento de usuários RDP
"""

import os
import pwd
import grp
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RDPUser:
    """Representa um usuário RDP"""

    def __init__(self, username: str, uid: int, home_dir: str,
                 desktop_env: str, rdp_port: int, active: bool = False, enabled: bool = True,
                 is_superuser: bool = False, session_type: str = 'desktop',
                 app_command: str = '', app_args: str = ''):
        self.username = username
        self.uid = uid
        self.home_dir = home_dir
        self.desktop_env = desktop_env
        self.rdp_port = rdp_port
        self.active = active
        self.enabled = enabled  # Se a conta está habilitada (não bloqueada)
        self.is_superuser = is_superuser  # Se o usuário tem privilégios sudo
        self.session_type = session_type  # 'desktop', 'remoteapp', ou 'winege-remoteapp'
        self.app_command = app_command  # Comando do app para RemoteApp (ex: 'firefox') ou .exe path para WineGE
        self.app_args = app_args  # Argumentos do app (ex: '--private-window')

    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'username': self.username,
            'uid': self.uid,
            'home_dir': self.home_dir,
            'desktop_env': self.desktop_env,
            'rdp_port': self.rdp_port,
            'active': self.active,
            'enabled': self.enabled,
            'is_superuser': self.is_superuser,
            'session_type': self.session_type,
            'app_command': self.app_command,
            'app_args': self.app_args
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RDPUser':
        """Cria instância a partir de dicionário"""
        return cls(**data)


class UserManager:
    """Gerenciador de usuários RDP"""

    # UID inicial para usuários RDP (fora da faixa de usuários normais)
    RDP_UID_START = 5000

    # Cache de estados de usuários (enabled/disabled)
    # Usado quando não temos permissão para verificar /etc/shadow
    _user_states_cache = {}
    RDP_GID_NAME = "rdp-users"

    def __init__(self, app_config=None, rdp_users_home: str = "/opt/rdp-users"):
        self.app_config = app_config
        self.rdp_users_home = Path(rdp_users_home)
        self.config_file = self.rdp_users_home / "users.conf"
        # Cache persistente de estados de usuários
        self.states_cache_file = Path.home() / ".config" / "rdp-session-manager" / "user_states.json"
        self._ensure_base_setup()
        self._load_states_cache()

    def _ensure_base_setup(self):
        """Garante que a estrutura base existe"""
        try:
            # Criar diretório base se não existir
            if not self.rdp_users_home.exists():
                logger.info(f"Criando diretório base: {self.rdp_users_home}")
                # Será criado via PolicyKit helper

            # Garantir que o grupo rdp-users existe
            self._ensure_rdp_group()

        except Exception as e:
            logger.error(f"Erro ao configurar estrutura base: {e}")

    def _ensure_rdp_group(self) -> int:
        """Garante que o grupo rdp-users existe"""
        try:
            group = grp.getgrnam(self.RDP_GID_NAME)
            return group.gr_gid
        except KeyError:
            # Grupo não existe, precisa ser criado via PolicyKit
            logger.warning(f"Grupo {self.RDP_GID_NAME} não existe")
            return -1

    def _load_states_cache(self):
        """Carrega o cache persistente de estados dos usuários"""
        try:
            if self.states_cache_file.exists():
                with open(self.states_cache_file, 'r') as f:
                    cached_states = json.load(f)
                    # Atualizar o cache em memória
                    UserManager._user_states_cache.update(cached_states)
                    logger.debug(f"Cache de estados carregado: {cached_states}")
        except Exception as e:
            logger.warning(f"Erro ao carregar cache de estados: {e}")

    def _save_states_cache(self):
        """Salva o cache de estados dos usuários em arquivo"""
        try:
            # Criar diretório se não existir
            self.states_cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.states_cache_file, 'w') as f:
                json.dump(UserManager._user_states_cache, f, indent=2)
                logger.debug(f"Cache de estados salvo: {UserManager._user_states_cache}")
        except Exception as e:
            logger.error(f"Erro ao salvar cache de estados: {e}")

    def _get_next_uid(self) -> int:
        """Obtém o próximo UID disponível para usuários RDP"""
        existing_uids = [user.uid for user in self.list_users()]

        uid = self.RDP_UID_START
        while uid in existing_uids:
            uid += 1

        return uid

    def create_user(self, username: str, password: str, desktop_env: str,
                   full_name: str = "", session_type: str = 'desktop',
                   app_command: str = '', app_args: str = '', log_callback=None) -> Optional[RDPUser]:
        """
        Cria um novo usuário RDP

        Args:
            username: Nome de usuário
            password: Senha do usuário
            desktop_env: Ambiente desktop (gnome, xfce, kde) - usado apenas se session_type='desktop'
            full_name: Nome completo do usuário
            session_type: Tipo de sessão ('desktop', 'remoteapp', ou 'winege-remoteapp')
            app_command: Comando do aplicativo para RemoteApp (ex: 'firefox') ou caminho .exe para WineGE
            app_args: Argumentos do aplicativo (ex: '--private-window')

        Returns:
            RDPUser se sucesso, None se falha
        """
        logger.info("=" * 70)
        logger.info("USER_MANAGER: Método create_user() CHAMADO")
        logger.info(f"  - Username: {username}")
        logger.info(f"  - Session Type: {session_type}")
        if session_type == 'desktop':
            logger.info(f"  - Desktop ENV: {desktop_env}")
        else:
            logger.info(f"  - App Command: {app_command}")
            logger.info(f"  - App Args: {app_args}")
        logger.info(f"  - Full name: {full_name}")
        logger.info("=" * 70)

        try:
            def log(msg):
                logger.info(f"USER_MANAGER: {msg}")
                if log_callback:
                    log_callback(msg)

            # Validar nome de usuário
            log("→ Validando nome de usuário...")
            if not self._validate_username(username):
                logger.error(f"Nome de usuário inválido: {username}")
                raise ValueError(f"Nome de usuário inválido: {username}")
            log("  OK Nome de usuário válido")

            # Verificar se usuário já existe
            log("→ Verificando se usuário já existe...")
            if self.user_exists(username):
                logger.error(f"Usuário já existe: {username}")
                raise ValueError(f"Usuário já existe: {username}")
            log("  OK Usuário disponível")

            # Obter UID e porta global
            log("→ Alocando UID...")
            uid = self._get_next_uid()
            home_dir = str(self.rdp_users_home / username)

            # Obter porta da configuração global
            rdp_port = self.app_config.get_default_rdp_port() if self.app_config else 3389

            log(f"  UID: {uid}")
            log(f"  Porta RDP: {rdp_port} (porta global)")
            log(f"  Home: {home_dir}")

            # Criar grupo rdp-users se não existir
            log("")
            log("→ Verificando grupo rdp-users...")
            self._ensure_rdp_group_exists(log_callback=log)

            # Criar diretório base se não existir
            log("")
            log("→ Verificando diretório base...")
            self._create_base_directory(log_callback=log)

            # Criar usuário via pkexec
            log("")
            log("→ Criando usuário no sistema...")
            log("  AVISO Você será solicitado a autenticar (pkexec)")
            success = self._create_system_user(username, password, uid, home_dir, full_name, desktop_env,
                                               session_type, app_command, app_args, log_callback=log)

            if not success:
                raise Exception("Falha ao criar usuário no sistema")

            rdp_user = RDPUser(
                username=username,
                uid=uid,
                home_dir=home_dir,
                desktop_env=desktop_env,
                rdp_port=rdp_port,
                active=False,
                is_superuser=False,  # Novos usuários não têm sudo por padrão
                session_type=session_type,
                app_command=app_command,
                app_args=app_args
            )

            log("")
            log("OK Usuário criado no sistema com sucesso!")
            logger.info("=" * 70)
            logger.info(f"USER_MANAGER: SUCESSO - Usuário RDP criado!")
            logger.info(f"  - Username: {username}")
            logger.info(f"  - UID: {uid}")
            logger.info(f"  - Porta RDP: {rdp_port}")
            logger.info(f"  - Home: {home_dir}")
            logger.info(f"  - Desktop ENV: {desktop_env}")
            logger.info("=" * 70)

            # Adicionar ao cache como habilitado (usuários novos são criados habilitados)
            UserManager._user_states_cache[username] = True
            self._save_states_cache()

            return rdp_user

        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"USER_MANAGER: ERRO ao criar usuário {username}")
            logger.error(f"  - Exceção: {type(e).__name__}")
            logger.error(f"  - Mensagem: {e}")
            logger.error("=" * 70)
            if log_callback:
                log_callback(f"X ERRO: {e}")
            raise

    def _ensure_rdp_group_exists(self, log_callback=None):
        """Garante que o grupo rdp-users existe"""
        try:
            grp.getgrnam(self.RDP_GID_NAME)
            logger.info(f"Grupo {self.RDP_GID_NAME} já existe")
            if log_callback:
                log_callback(f"  OK Grupo '{self.RDP_GID_NAME}' já existe")
        except KeyError:
            # Criar grupo
            logger.info(f"Criando grupo {self.RDP_GID_NAME}...")
            if log_callback:
                log_callback(f"  → Criando grupo '{self.RDP_GID_NAME}'...")
                log_callback(f"  AVISO Você será solicitado a autenticar (pkexec)")
                log_callback(f"  $ pkexec /usr/sbin/groupadd {self.RDP_GID_NAME}")

            result = subprocess.run(
                ['pkexec', '/usr/sbin/groupadd', self.RDP_GID_NAME],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Verificar se foi cancelado pelo usuário
                if result.returncode == 126:
                    error_msg = "Autenticação cancelada pelo usuário"
                elif result.returncode == 127:
                    error_msg = "pkexec não encontrado - instale o policykit-1"
                else:
                    error_msg = f"Código: {result.returncode}, stderr: {result.stderr}"

                logger.error(f"Falha ao criar grupo rdp-users: {error_msg}")
                raise Exception(f"Falha ao criar grupo rdp-users: {error_msg}")

            if log_callback:
                log_callback(f"  OK Grupo '{self.RDP_GID_NAME}' criado com sucesso")

    def _create_base_directory(self, log_callback=None):
        """Cria diretório base /opt/rdp-users"""
        if not self.rdp_users_home.exists():
            logger.info(f"Criando diretório base {self.rdp_users_home}...")
            if log_callback:
                log_callback(f"  → Criando diretório {self.rdp_users_home}...")
                log_callback(f"  AVISO Você será solicitado a autenticar (pkexec)")
                log_callback(f"  $ pkexec mkdir -p {self.rdp_users_home}")

            result = subprocess.run(
                ['pkexec', '/usr/bin/mkdir', '-p', str(self.rdp_users_home)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if result.returncode == 126:
                    error_msg = "Autenticação cancelada pelo usuário"
                elif result.returncode == 127:
                    error_msg = "pkexec não encontrado - instale o policykit-1"
                else:
                    error_msg = f"Código: {result.returncode}, stderr: {result.stderr}"

                logger.error(f"Falha ao criar diretório: {error_msg}")
                raise Exception(f"Falha ao criar diretório /opt/rdp-users: {error_msg}")

            # Definir permissões
            if log_callback:
                log_callback(f"  $ pkexec chmod 755 {self.rdp_users_home}")

            chmod_result = subprocess.run(
                ['pkexec', '/usr/bin/chmod', '755', str(self.rdp_users_home)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if chmod_result.returncode != 0:
                logger.warning(f"Aviso ao definir permissões: {chmod_result.stderr}")

            if log_callback:
                log_callback(f"  OK Diretório criado com sucesso")
        else:
            if log_callback:
                log_callback(f"  OK Diretório {self.rdp_users_home} já existe")

    def _create_system_user(self, username: str, password: str, uid: int,
                           home_dir: str, full_name: str, desktop_env: str,
                           session_type: str = 'desktop', app_command: str = '',
                           app_args: str = '', log_callback=None) -> bool:
        """Cria usuário no sistema via pkexec usando script helper"""
        try:
            # Obter caminho do script helper
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            create_script = script_dir / "create-rdp-user.sh"
            password_script = script_dir / "set-user-password.sh"

            # Mapear desktop_env para comando DE (usado apenas para desktop mode)
            de_commands = {
                'gnome': 'gnome-session',
                'xfce': 'startxfce4',
                'xfce4': 'startxfce4',
                'kde': 'startplasma-x11',
                'plasma': 'startplasma-x11',
                'mate': 'mate-session',
                'cinnamon': 'cinnamon-session',
                'lxde': 'startlxde',
                'lxqt': 'startlxqt',
            }
            de_command = de_commands.get(desktop_env.lower(), 'startxfce4')

            if log_callback:
                log_callback(f"  → Criando usuário e configurando sistema...")
                log_callback(f"  AVISO Você será solicitado a autenticar (apenas uma vez)")

            # Executar script de criação de usuário
            # Passar: username, uid, home_dir, full_name, session_type, de_command_or_app, app_args
            if session_type in ['remoteapp', 'winege-remoteapp']:
                session_command = app_command
                extra_args = app_args
            else:
                session_command = de_command
                extra_args = ""

            cmd = [
                'pkexec', str(create_script),
                username,
                str(uid),
                home_dir,
                full_name or "",
                session_type,  # 'desktop' ou 'remoteapp'
                session_command,  # Comando DE ou app
                extra_args  # Args do app (vazio para desktop)
            ]

            logger.info(f"Executando script helper: {create_script.name}")

            # Para WineGE, precisamos de timeout maior (download + setup = ~15min)
            timeout_seconds = 1200 if session_type == 'winege-remoteapp' else 30
            if session_type == 'winege-remoteapp':
                logger.info(f"  AVISO WineGE pode levar 10-15 minutos para download e instalação")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)

            if result.returncode != 0:
                # Verificar código de erro
                if result.returncode == 126:
                    error_msg = "Autenticação cancelada pelo usuário"
                elif result.returncode == 127:
                    error_msg = "Script helper não encontrado"
                else:
                    error_msg = f"Código: {result.returncode}, Erro: {result.stderr.strip()}"

                logger.error(f"Criação de usuário falhou: {error_msg}")
                if log_callback:
                    log_callback(f"  X Erro na criação: {error_msg}")
                return False

            # Exibir output do script
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"  {line}")
                    if log_callback:
                        log_callback(f"  {line}")

            # Definir senha (segunda autenticação pkexec)
            if log_callback:
                log_callback(f"  → Definindo senha...")
                log_callback(f"  AVISO Você será solicitado a autenticar novamente")

            echo_proc = subprocess.Popen(
                ['echo', f'{username}:{password}'],
                stdout=subprocess.PIPE
            )

            passwd_proc = subprocess.Popen(
                ['pkexec', str(password_script)],
                stdin=echo_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            echo_proc.stdout.close()
            stdout, stderr = passwd_proc.communicate()

            if passwd_proc.returncode != 0:
                # Verificar código de erro
                if passwd_proc.returncode == 126:
                    error_msg = "Autenticação cancelada pelo usuário"
                else:
                    error_msg = f"Código: {passwd_proc.returncode}, stderr: {stderr.decode().strip()}"

                logger.error(f"Definição de senha falhou: {error_msg}")
                if log_callback:
                    log_callback(f"  X Erro ao definir senha: {error_msg}")
                return False

            if log_callback:
                log_callback(f"  OK Senha definida com sucesso")

            logger.info(f"Usuário {username} criado no sistema com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao criar usuário no sistema: {e}")
            if log_callback:
                log_callback(f"  X Erro: {e}")
            return False

    def get_user_processes(self, username: str) -> List[int]:
        """
        Obtém lista de PIDs de processos do usuário

        Args:
            username: Nome do usuário

        Returns:
            Lista de PIDs
        """
        try:
            result = subprocess.run(
                ['pgrep', '-u', username],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Retornar PIDs
                pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
                return pids

            # Se returncode != 0, não há processos
            return []

        except Exception as e:
            logger.error(f"Erro ao verificar processos do usuário {username}: {e}")
            return []

    def kill_user_processes(self, username: str, force: bool = False) -> bool:
        """
        Mata todos os processos de um usuário

        Args:
            username: Nome do usuário
            force: Se True, usa SIGKILL (-9), senão usa SIGTERM (-15)

        Returns:
            True se sucesso
        """
        try:
            signal = '-9' if force else '-15'

            logger.info(f"Terminando processos do usuário {username} (signal: {signal})...")

            # Primeiro tentar SIGTERM
            result = subprocess.run(
                ['pkexec', '/usr/bin/pkill', signal, '-u', username],
                capture_output=True,
                text=True,
                timeout=10
            )

            # pkill retorna 0 se encontrou processos, 1 se não encontrou
            # Ambos são ok
            if result.returncode in [0, 1]:
                logger.info(f"Processos do usuário {username} terminados")
                return True
            else:
                logger.warning(f"pkill retornou código {result.returncode}: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Erro ao terminar processos do usuário {username}: {e}")
            return False

    def delete_user(self, username: str, remove_home: bool = True, kill_processes: bool = True) -> bool:
        """
        Remove um usuário RDP usando script helper

        Args:
            username: Nome do usuário
            remove_home: Se True, remove o diretório home
            kill_processes: Se True, mata processos do usuário antes de deletar

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                raise ValueError(f"Usuário não existe: {username}")

            logger.info(f"Removendo usuário RDP: {username}")

            # Verificar se há processos ativos (apenas para log)
            active_pids = self.get_user_processes(username)
            if active_pids:
                logger.info(f"Usuário {username} tem {len(active_pids)} processos ativos")

            # Usar script helper que agrupa: pkill + userdel em uma única autenticação
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            delete_script = script_dir / "delete-rdp-user.sh"

            # Montar comando com flags
            cmd = ['pkexec', str(delete_script), username]

            if remove_home:
                cmd.append('--remove-home')

            if kill_processes:
                cmd.append('--kill-processes')

            logger.info(f"Executando script helper para deletar {username}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Deleção falhou: {result.stderr}")
                raise Exception(f"Falha ao remover usuário: {result.stderr}")

            # Exibir output do script
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"  {line}")

            logger.info(f"OK Usuário {username} removido com sucesso")
            logger.info(f"  - Diretório home removido: {remove_home}")
            logger.info(f"  - Processos terminados: {kill_processes}")

            # Remover do cache e persistir
            if username in UserManager._user_states_cache:
                del UserManager._user_states_cache[username]
                self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Erro ao remover usuário {username}: {e}")
            raise

    def lock_user(self, username: str) -> bool:
        """
        Desabilita (bloqueia) um usuário RDP

        Args:
            username: Nome do usuário

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Desabilitando usuário: {username}")

            # Usar script helper para lock
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            toggle_script = script_dir / "toggle-user-lock.sh"

            cmd = ['pkexec', str(toggle_script), username, 'lock']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao desabilitar usuário: {result.stderr}")
                return False

            logger.info(f"OK Usuário {username} desabilitado com sucesso")

            # Atualizar cache em memória e persistir em arquivo
            UserManager._user_states_cache[username] = False
            self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Erro ao desabilitar usuário {username}: {e}")
            return False

    def unlock_user(self, username: str) -> bool:
        """
        Habilita (desbloqueia) um usuário RDP

        Args:
            username: Nome do usuário

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Habilitando usuário: {username}")

            # Usar script helper para unlock
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            toggle_script = script_dir / "toggle-user-lock.sh"

            cmd = ['pkexec', str(toggle_script), username, 'unlock']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao habilitar usuário: {result.stderr}")
                return False

            logger.info(f"OK Usuário {username} habilitado com sucesso")

            # Atualizar cache em memória e persistir em arquivo
            UserManager._user_states_cache[username] = True
            self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Erro ao habilitar usuário {username}: {e}")
            return False

    def grant_sudo(self, username: str, kill_sessions: bool = True) -> bool:
        """
        Concede privilégios de superusuário (sudo) para um usuário RDP

        Args:
            username: Nome do usuário
            kill_sessions: Se True, encerra sessões ativas para aplicar mudanças

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Concedendo privilégios sudo para: {username}")

            # Verificar se usuário tem processos ativos
            active_pids = self.get_user_processes(username)
            if active_pids and kill_sessions:
                logger.info(f"Usuário {username} tem {len(active_pids)} processos ativos - serão encerrados")
                logger.info("IMPORTANTE: Mudanças de grupo só têm efeito após logout/login")

            # Usar script helper para conceder sudo
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            sudo_script = script_dir / "toggle-user-sudo.sh"

            cmd = ['pkexec', str(sudo_script), username, 'grant']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao conceder privilégios sudo: {result.stderr}")
                return False

            logger.info(f"OK Privilégios sudo concedidos para {username}")

            # Encerrar sessões ativas para forçar reconexão
            if active_pids and kill_sessions:
                logger.info(f"Encerrando sessões de {username} para aplicar mudanças...")
                self.kill_user_processes(username, force=False)

            return True

        except Exception as e:
            logger.error(f"Erro ao conceder privilégios sudo para {username}: {e}")
            return False

    def revoke_sudo(self, username: str, kill_sessions: bool = True) -> bool:
        """
        Revoga privilégios de superusuário (sudo) de um usuário RDP

        Args:
            username: Nome do usuário
            kill_sessions: Se True, encerra sessões ativas para aplicar mudanças

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Revogando privilégios sudo de: {username}")

            # Verificar se usuário tem processos ativos
            active_pids = self.get_user_processes(username)
            if active_pids and kill_sessions:
                logger.info(f"Usuário {username} tem {len(active_pids)} processos ativos - serão encerrados")
                logger.info("IMPORTANTE: Mudanças de grupo só têm efeito após logout/login")

            # Usar script helper para revogar sudo
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            sudo_script = script_dir / "toggle-user-sudo.sh"

            cmd = ['pkexec', str(sudo_script), username, 'revoke']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao revogar privilégios sudo: {result.stderr}")
                return False

            logger.info(f"OK Privilégios sudo revogados de {username}")

            # Encerrar sessões ativas para forçar reconexão
            if active_pids and kill_sessions:
                logger.info(f"Encerrando sessões de {username} para aplicar mudanças...")
                self.kill_user_processes(username, force=False)

            return True

        except Exception as e:
            logger.error(f"Erro ao revogar privilégios sudo de {username}: {e}")
            return False

    def is_superuser(self, username: str) -> bool:
        """
        Verifica se um usuário tem privilégios de superusuário (está no grupo sudo)

        Args:
            username: Nome do usuário

        Returns:
            True se o usuário tem privilégios sudo, False caso contrário
        """
        try:
            # Usar 'id -nG' para obter todos os grupos do usuário de forma confiável
            # Este comando retorna todos os grupos, incluindo secundários
            result = subprocess.run(
                ['id', '-nG', username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Obter lista de grupos
                groups = result.stdout.strip().split()
                # Verificar se 'sudo' está na lista
                has_sudo = 'sudo' in groups
                logger.debug(f"User {username} groups: {groups}, has sudo: {has_sudo}")
                return has_sudo

            # Se o comando falhou, tentar método alternativo
            logger.warning(f"Command 'id -nG {username}' failed, trying alternative method")

            # Método alternativo: verificar diretamente no grupo
            sudo_group = grp.getgrnam('sudo')
            return username in sudo_group.gr_mem

        except KeyError:
            # Grupo sudo não existe
            logger.warning("Grupo 'sudo' não encontrado no sistema")
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar privilégios sudo de {username}: {e}")
            return False

    def user_exists(self, username: str) -> bool:
        """Verifica se um usuário RDP existe"""
        try:
            pwd.getpwnam(username)
            # Verificar se está no grupo rdp-users
            return True
        except KeyError:
            return False

    def _is_rdp_user(self, username: str) -> bool:
        """Verifica se um usuário pertence ao grupo rdp-users"""
        try:
            group = grp.getgrnam(self.RDP_GID_NAME)
            return username in group.gr_mem
        except KeyError:
            # Grupo não existe ainda
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar grupo do usuário {username}: {e}")
            return False

    def _is_user_enabled(self, username: str) -> bool:
        """
        Verifica se um usuário está habilitado (não bloqueado)
        NOTA: Requer privilégios de root, use _check_user_enabled_from_shadow para verificação sem privilégios

        Args:
            username: Nome do usuário

        Returns:
            True se habilitado, False se bloqueado
        """
        try:
            # Usar passwd -S para verificar status da conta
            # Formato da saída: username STATUS ....
            # STATUS: P (password set), L (locked), NP (no password)
            result = subprocess.run(
                ['passwd', '-S', username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # A segunda palavra indica o status
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    status = parts[1]
                    # 'L' indica locked (bloqueado)
                    return status != 'L'

            # Por padrão, assumir que está habilitado
            return True

        except Exception as e:
            logger.error(f"Erro ao verificar status de {username}: {e}")
            return True  # Por padrão, assumir habilitado

    def _check_user_enabled_from_shadow(self, username: str) -> bool:
        """
        Verifica se usuário está habilitado lendo /etc/shadow diretamente
        Usa cache se não tiver permissões para verificar

        Args:
            username: Nome do usuário

        Returns:
            True se habilitado, False se bloqueado
        """
        try:
            # Tentar usar getent shadow (pode funcionar em alguns sistemas)
            result = subprocess.run(
                ['getent', 'shadow', username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout:
                # Formato: username:password:lastchg:min:max:warn:inactive:expire:reserved
                # Se password começa com '!' ou '!!' está bloqueado
                parts = result.stdout.strip().split(':')
                if len(parts) >= 2:
                    password_field = parts[1]
                    # Bloqueado se começa com '!' ou '!!'
                    is_locked = password_field.startswith('!')
                    enabled = not is_locked

                    # Atualizar cache com valor real
                    UserManager._user_states_cache[username] = enabled
                    return enabled

            # Se não conseguiu verificar diretamente, usar cache
            if username in UserManager._user_states_cache:
                logger.debug(f"Usando cache para status de {username}: {UserManager._user_states_cache[username]}")
                return UserManager._user_states_cache[username]

            # Se não tem no cache, assumir habilitado
            # (novos usuários são criados habilitados por padrão)
            logger.debug(f"Sem cache para {username}, assumindo habilitado")
            return True

        except Exception as e:
            logger.debug(f"Não foi possível verificar status de {username}: {e}")
            # Tentar usar cache
            if username in UserManager._user_states_cache:
                return UserManager._user_states_cache[username]
            return True  # Por padrão, assumir habilitado

    def _detect_session_info(self, home_dir: str) -> tuple:
        """
        Detecta informações de sessão do usuário do arquivo .xsession

        Returns:
            tuple: (session_type, desktop_env_or_command, app_args)
        """
        try:
            xsession_file = Path(home_dir) / '.xsession'

            if not xsession_file.exists():
                logger.warning(f"Arquivo .xsession não encontrado em {home_dir}")
                return ('desktop', 'unknown', '')

            # Ler arquivo .xsession
            with open(xsession_file, 'r') as f:
                content = f.read()

            # Detectar se é WineGE RemoteApp
            if 'Mode: WineGE RemoteApp' in content or '.launch_winege_app.sh' in content:
                # WineGE RemoteApp mode - ler o caminho do .exe
                winege_app_path = Path(home_dir) / '.winege_app_path'
                if winege_app_path.exists():
                    with open(winege_app_path, 'r') as f:
                        exe_path = f.read().strip()
                        logger.debug(f"Detected WineGE RemoteApp: {exe_path}")
                        return ('winege-remoteapp', exe_path, '')
                return ('winege-remoteapp', 'unknown', '')

            # Detectar se é RemoteApp ou Desktop (RemoteApp usa openbox)
            if 'Mode: RemoteApp' in content or 'openbox' in content:
                # RemoteApp mode - extrair comando do app
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('exec ') and not any(wm in line for wm in ['openbox', 'metacity', 'dbus-launch', 'winege']):
                        # Extrair comando e argumentos
                        exec_cmd = line[5:].strip()  # Remove "exec "
                        parts = exec_cmd.split(maxsplit=1)
                        app_command = parts[0] if parts else ''
                        app_args = parts[1] if len(parts) > 1 else ''
                        logger.debug(f"Detected RemoteApp: {app_command} {app_args}")
                        return ('remoteapp', app_command, app_args)
                return ('remoteapp', 'unknown', '')
            else:
                # Desktop mode - detectar DE
                de_commands = {
                    'startlxde': 'lxde',
                    'startlxqt': 'lxqt',
                    'startxfce4': 'xfce',
                    'mate-session': 'mate',
                    'cinnamon-session': 'cinnamon',
                    'gnome-session': 'gnome',
                    'startplasma-x11': 'kde'
                }

                for command, de_id in de_commands.items():
                    if command in content:
                        logger.debug(f"Detected DE for {home_dir}: {de_id} (command: {command})")
                        return ('desktop', de_id, '')

                logger.warning(f"Comando DE não reconhecido em {xsession_file}")
                return ('desktop', 'unknown', '')

        except Exception as e:
            logger.error(f"Erro ao detectar sessão de {home_dir}: {e}")
            return ('desktop', 'unknown', '')

    def _detect_desktop_env(self, home_dir: str) -> str:
        """Detecta o Desktop Environment lendo o arquivo .xsession"""
        session_type, desktop_env_or_cmd, _ = self._detect_session_info(home_dir)
        if session_type in ['remoteapp', 'winege-remoteapp']:
            return session_type  # Para usuários RemoteApp, retorna o tipo como DE
        return desktop_env_or_cmd

    def _detect_rdp_port(self, uid: int) -> int:
        """Detecta a porta RDP baseada na configuração global"""
        # Usar porta global da configuração (todos os usuários na mesma porta)
        if self.app_config:
            return self.app_config.get_default_rdp_port()
        return 3389  # Fallback

    def list_users(self) -> List[RDPUser]:
        """Lista todos os usuários RDP"""
        users = []

        try:
            # Verificar se o grupo rdp-users existe
            try:
                rdp_group = grp.getgrnam(self.RDP_GID_NAME)
            except KeyError:
                # Grupo não existe, não há usuários RDP ainda
                return users

            # Listar apenas usuários do grupo rdp-users
            for user_info in pwd.getpwall():
                # Verificar se o usuário está no grupo rdp-users
                if self._is_rdp_user(user_info.pw_name) or user_info.pw_gid == rdp_group.gr_gid:
                    # Detectar informações de sessão (tipo, DE/app, args)
                    session_type, desktop_env_or_cmd, app_args = self._detect_session_info(user_info.pw_dir)

                    # Para desktop mode, desktop_env_or_cmd é o DE
                    # Para remoteapp/winege-remoteapp mode, desktop_env_or_cmd é o comando do app ou .exe
                    if session_type in ['remoteapp', 'winege-remoteapp']:
                        desktop_env = session_type
                        app_command = desktop_env_or_cmd
                    else:
                        desktop_env = desktop_env_or_cmd
                        app_command = ''
                        app_args = ''

                    # Detectar porta RDP baseada no UID
                    rdp_port = self._detect_rdp_port(user_info.pw_uid)

                    # Verificar se usuário está habilitado através de /etc/shadow
                    # (não requer privilégios para ler se o arquivo tem permissões corretas)
                    is_enabled = self._check_user_enabled_from_shadow(user_info.pw_name)

                    # Verificar se usuário tem privilégios sudo
                    has_sudo = self.is_superuser(user_info.pw_name)

                    rdp_user = RDPUser(
                        username=user_info.pw_name,
                        uid=user_info.pw_uid,
                        home_dir=user_info.pw_dir,
                        desktop_env=desktop_env,
                        rdp_port=rdp_port,
                        active=False,  # TODO: verificar status
                        enabled=is_enabled,
                        is_superuser=has_sudo,
                        session_type=session_type,
                        app_command=app_command,
                        app_args=app_args
                    )
                    users.append(rdp_user)

        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")

        return users

    def get_user(self, username: str) -> Optional[RDPUser]:
        """Obtém informações de um usuário específico"""
        for user in self.list_users():
            if user.username == username:
                return user
        return None

    def _validate_username(self, username: str) -> bool:
        """Valida nome de usuário"""
        import re

        # Lista de nomes de usuário reservados do sistema
        RESERVED_USERNAMES = {
            'root', 'admin', 'administrator', 'daemon', 'bin', 'sys', 'sync',
            'games', 'man', 'lp', 'mail', 'news', 'uucp', 'proxy', 'www-data',
            'backup', 'list', 'irc', 'gnats', 'nobody', 'systemd-network',
            'systemd-resolve', 'messagebus', 'systemd-timesync', 'syslog',
            'avahi-autoipd', 'usbmux', 'dnsmasq', 'rtkit', 'cups-pk-helper',
            'speech-dispatcher', 'avahi', 'pulse', 'saned', 'colord', 'hplip',
            'geoclue', 'gnome-initial-setup', 'gdm', 'postgres', 'mysql',
            'ftp', 'ssh', 'sshd'
        }

        # Verificar se é nome reservado
        if username.lower() in RESERVED_USERNAMES:
            logger.error(f"Nome de usuário '{username}' é reservado do sistema")
            return False

        # Nome deve começar com letra, conter apenas letras, números, - e _
        # Comprimento entre 3 e 32 caracteres
        pattern = r'^[a-z][a-z0-9_-]{2,31}$'
        return bool(re.match(pattern, username))

    def change_password(self, username: str, new_password: str) -> bool:
        """
        Altera senha de um usuário RDP

        Args:
            username: Nome do usuário
            new_password: Nova senha

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Alterando senha do usuário: {username}")

            # Usar script helper para alterar senha
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            password_script = script_dir / "set-user-password.sh"

            # Usar echo e pipe para passar a senha
            echo_proc = subprocess.Popen(
                ['echo', f'{username}:{new_password}'],
                stdout=subprocess.PIPE
            )

            passwd_proc = subprocess.Popen(
                ['pkexec', str(password_script)],
                stdin=echo_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            echo_proc.stdout.close()
            stdout, stderr = passwd_proc.communicate(timeout=30)

            if passwd_proc.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"Falha ao alterar senha: {error_msg}")
                return False

            logger.info(f"OK Senha de {username} alterada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao alterar senha de {username}: {e}")
            return False

    def rename_user(self, old_username: str, new_username: str) -> bool:
        """
        Renomeia um usuário RDP

        Args:
            old_username: Nome atual do usuário
            new_username: Novo nome do usuário

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(old_username):
                logger.error(f"Usuário não existe: {old_username}")
                return False

            if self.user_exists(new_username):
                logger.error(f"Usuário já existe: {new_username}")
                return False

            # Validar novo nome
            if not self._validate_username(new_username):
                logger.error(f"Nome de usuário inválido: {new_username}")
                return False

            logger.info(f"Renomeando usuário: {old_username} -> {new_username}")

            # Usar script helper para renomear usuário
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            rename_script = script_dir / "rename-user.sh"

            cmd = ['pkexec', str(rename_script), old_username, new_username]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao renomear usuário: {result.stderr}")
                return False

            logger.info(f"OK Usuário renomeado: {old_username} -> {new_username}")

            # Atualizar cache de estados
            if old_username in UserManager._user_states_cache:
                UserManager._user_states_cache[new_username] = UserManager._user_states_cache.pop(old_username)
                self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Erro ao renomear usuário {old_username}: {e}")
            return False

    def change_user_fullname(self, username: str, new_fullname: str) -> bool:
        """
        Altera o nome completo (GECOS) de um usuário RDP

        Args:
            username: Nome do usuário
            new_fullname: Novo nome completo

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Alterando nome completo de {username} para: {new_fullname}")

            # Usar script helper para alterar GECOS
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            chfn_script = script_dir / "change-user-fullname.sh"

            cmd = ['pkexec', str(chfn_script), username, new_fullname]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao alterar nome completo: {result.stderr}")
                return False

            logger.info(f"OK Nome completo de {username} alterado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao alterar nome completo de {username}: {e}")
            return False

    def list_user_executables(self, username: str) -> list:
        """
        Lista todos os executáveis disponíveis para um usuário WineGE

        Args:
            username: Nome do usuário

        Returns:
            Lista de caminhos de executáveis disponíveis
        """
        try:
            if not self.user_exists(username):
                return []

            user_home = self.rdp_users_home / username
            executables = []

            # Buscar em WindowsApps (portáteis)
            windows_apps = user_home / "WindowsApps"
            if windows_apps.exists():
                for exe in windows_apps.glob("*.exe"):
                    executables.append(("WindowsApps", str(exe)))

            # Buscar instalados no Wine
            wine_prefix = user_home / ".wine" / "drive_c"
            if wine_prefix.exists():
                program_files = [
                    wine_prefix / "Program Files",
                    wine_prefix / "Program Files (x86)"
                ]

                for pf in program_files:
                    if pf.exists():
                        for exe in pf.rglob("*.exe"):
                            exe_name_lower = exe.name.lower()
                            # Filtrar aplicativos padrão do Windows e uninstallers
                            if not any(x in str(exe).lower() for x in [
                                'unins', 'uninst', 'windows nt', 'internet explorer',
                                'windows media', 'windows mail', 'windows photo',
                                'wordpad', 'notepad'
                            ]):
                                executables.append(("Wine", str(exe)))

            return executables

        except Exception as e:
            logger.error(f"Erro ao listar executáveis de {username}: {e}")
            return []

    def update_winege_executable(self, username: str, new_exe_path: str) -> bool:
        """
        Atualiza o executável WineGE de um usuário existente

        Args:
            username: Nome do usuário
            new_exe_path: Caminho do novo executável .exe

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            logger.info(f"Atualizando executável WineGE de {username} para: {new_exe_path}")

            # Usar script helper para atualizar .exe
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            update_script = script_dir / "update-winege-exe.sh"

            cmd = ['pkexec', str(update_script), username, new_exe_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao atualizar executável: {result.stderr}")
                return False

            logger.info(f"OK Executável WineGE de {username} atualizado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar executável de {username}: {e}")
            return False

    def change_user_session_type(self, username: str, session_type: str,
                                 session_command: str = '', app_args: str = '') -> bool:
        """
        Altera o tipo de sessão de um usuário RDP (desktop <-> remoteapp <-> winege-remoteapp)

        Args:
            username: Nome do usuário
            session_type: Novo tipo ('desktop', 'remoteapp', ou 'winege-remoteapp')
            session_command: Comando DE (desktop), app (remoteapp), ou .exe path (winege-remoteapp)
            app_args: Argumentos do app (apenas remoteapp/winege-remoteapp)

        Returns:
            True se sucesso, False se falha
        """
        try:
            if not self.user_exists(username):
                logger.error(f"Usuário não existe: {username}")
                return False

            if session_type not in ['desktop', 'remoteapp', 'winege-remoteapp']:
                logger.error(f"Tipo de sessão inválido: {session_type}")
                return False

            logger.info(f"Alterando tipo de sessão de {username} para: {session_type}")

            # Verificar se usuário tem processos ativos
            active_pids = self.get_user_processes(username)
            if active_pids:
                logger.info(f"Usuário {username} tem {len(active_pids)} processos ativos - serão encerrados")

            # Usar script helper para alterar .xsession
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            change_script = script_dir / "change-session-type.sh"

            cmd = ['pkexec', str(change_script), username, session_type, session_command, app_args]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Falha ao alterar tipo de sessão: {result.stderr}")
                return False

            logger.info(f"OK Tipo de sessão de {username} alterado para {session_type}")
            return True

        except Exception as e:
            logger.error(f"Erro ao alterar tipo de sessão de {username}: {e}")
            return False
