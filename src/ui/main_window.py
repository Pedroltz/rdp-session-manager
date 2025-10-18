#!/usr/bin/env python3
"""
Main Window
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import logging
import subprocess
from pathlib import Path

from .user_dialog import UserDialog

logger = logging.getLogger(__name__)


@Gtk.Template(filename=str(Path(__file__).parent.parent.parent / "data" / "ui" / "main-window.ui"))
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'MainWindow'

    # UI elements from template
    main_stack = Gtk.Template.Child()
    users_listbox = Gtk.Template.Child()
    add_user_button = Gtk.Template.Child()
    empty_add_user_button = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    ip_row = Gtk.Template.Child()
    sessions_row = Gtk.Template.Child()
    copy_ip_button = Gtk.Template.Child()

    def __init__(self, application, user_manager, rdp_config, de_installer, session_monitor, system_deps, **kwargs):
        super().__init__(application=application, **kwargs)

        self.user_manager = user_manager
        self.rdp_config = rdp_config
        self.de_installer = de_installer
        self.session_monitor = session_monitor
        self.system_deps = system_deps

        # Adicionar toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        current_child = self.get_content()
        self.set_content(self.toast_overlay)
        self.toast_overlay.set_child(current_child)

        # Criar banner de aviso para xrdp
        self.xrdp_banner = None
        self.create_xrdp_warning_banner()

        self.setup_signals()
        self.update_server_info()
        self.update_xrdp_status()
        self.load_users()

        # Update UI periodically
        GLib.timeout_add_seconds(5, self.update_sessions_info)
        GLib.timeout_add_seconds(10, self.update_xrdp_status)

    def setup_signals(self):
        """Setup signal handlers"""
        self.add_user_button.connect('clicked', self.on_add_user)
        self.empty_add_user_button.connect('clicked', self.on_add_user)
        self.copy_ip_button.connect('clicked', self.on_copy_ip)
        self.search_entry.connect('search-changed', self.on_search_changed)

    def update_server_info(self):
        """Update server information"""
        # Get IP address
        ip = self.session_monitor.get_ip_address()
        self.ip_row.set_subtitle(ip)

        # Get active sessions count
        sessions_count = self.session_monitor.get_session_count()
        self.sessions_row.set_subtitle(f"{sessions_count} sessões ativas")

    def update_sessions_info(self):
        """Update sessions information periodically"""
        try:
            sessions_count = self.session_monitor.get_session_count()
            self.sessions_row.set_subtitle(f"{sessions_count} sessões ativas")

            # Update user status
            self.load_users()

        except Exception as e:
            logger.error(f"Error updating sessions: {e}")

        return True  # Continue timeout

    def load_users(self):
        """Load and display users"""
        # Clear existing rows
        while True:
            row = self.users_listbox.get_row_at_index(0)
            if row is None:
                break
            self.users_listbox.remove(row)

        # Get users
        users = self.user_manager.list_users()

        if not users:
            self.main_stack.set_visible_child_name('empty')
            return

        self.main_stack.set_visible_child_name('users_list')

        # Add user rows
        for user in users:
            row = self.create_user_row(user)
            self.users_listbox.append(row)

    def create_user_row(self, user):
        """Create a user row widget"""
        # Check if user is connected
        is_active = self.session_monitor.is_user_connected(user.username)

        # Create row
        row = Adw.ActionRow()
        row.set_title(user.username)
        row.set_subtitle(f"{user.desktop_env.upper()} • Porta {user.rdp_port} • IP: {self.session_monitor.get_ip_address()}")

        # Status label and switch
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Status label - mostra "Habilitado/Desabilitado" se não está ativo, "Conectado" se ativo
        if is_active:
            status_text = 'Conectado'
        elif user.enabled:
            status_text = 'Habilitado'
        else:
            status_text = 'Desabilitado'

        status_label = Gtk.Label(label=status_text)
        status_label.add_css_class('dim-label')
        status_label.set_margin_end(12)  # Espaço antes do switch

        status_box.append(status_label)

        # Enable/Disable Switch (à direita do status)
        enable_switch = Gtk.Switch()
        enable_switch.set_active(user.enabled)
        enable_switch.set_valign(Gtk.Align.CENTER)
        enable_switch.set_tooltip_text('Habilitar/Desabilitar usuário')
        enable_switch.connect('state-set', lambda s, state: self.on_user_toggle(user.username, state, s))
        status_box.append(enable_switch)

        row.add_suffix(status_box)

        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Connect button
        connect_btn = Gtk.Button(icon_name='network-wired-symbolic')
        connect_btn.add_css_class('flat')
        connect_btn.set_valign(Gtk.Align.CENTER)
        connect_btn.set_tooltip_text('Conectar via RDP')
        connect_btn.connect('clicked', lambda b: self.on_connect_rdp(user))

        # Delete button
        delete_btn = Gtk.Button(icon_name='user-trash-symbolic')
        delete_btn.add_css_class('flat')
        delete_btn.add_css_class('destructive-action')
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.set_tooltip_text('Remover usuário')
        delete_btn.connect('clicked', lambda b: self.on_delete_user(user.username))

        button_box.append(connect_btn)
        button_box.append(delete_btn)
        row.add_suffix(button_box)

        return row

    def create_xrdp_warning_banner(self):
        """Create warning banner for missing xrdp"""
        # Criar Banner
        self.xrdp_banner = Adw.Banner()
        self.xrdp_banner.set_title("⚠ Servidor xrdp não está instalado - A aplicação não funcionará sem ele")
        self.xrdp_banner.set_button_label("Instalar Agora")
        self.xrdp_banner.connect('button-clicked', self.on_install_xrdp_clicked)
        self.xrdp_banner.set_revealed(False)

        # Obter a ToolbarView
        toolbar_view = self.toast_overlay.get_child()

        if toolbar_view and isinstance(toolbar_view, Adw.ToolbarView):
            # Obter o box principal (conteúdo da toolbar)
            content = toolbar_view.get_content()

            if content and isinstance(content, Gtk.Box):
                # Inserir banner como primeiro filho do box
                content.prepend(self.xrdp_banner)

    def update_xrdp_status(self):
        """Update xrdp status and show/hide banner"""
        if not self.system_deps:
            return True

        xrdp_ready = self.system_deps.is_xrdp_ready()

        # Mostrar/ocultar banner
        if self.xrdp_banner:
            self.xrdp_banner.set_revealed(not xrdp_ready)

        # Bloquear botões de criar usuário
        self.add_user_button.set_sensitive(xrdp_ready)
        self.empty_add_user_button.set_sensitive(xrdp_ready)

        # Atualizar tooltip
        if not xrdp_ready:
            tooltip = "Instale o xrdp primeiro para criar usuários RDP"
            self.add_user_button.set_tooltip_text(tooltip)
            self.empty_add_user_button.set_tooltip_text(tooltip)
        else:
            self.add_user_button.set_tooltip_text("Adicionar novo usuário RDP")
            self.empty_add_user_button.set_tooltip_text("Adicionar novo usuário RDP")

        return True  # Continue periodic check

    def on_install_xrdp_clicked(self, banner):
        """Handle install xrdp button click from banner"""
        # Chamar método da aplicação para instalar xrdp
        app = self.get_application()
        if app:
            app.show_xrdp_install_dialog()

    def on_add_user(self, button):
        """Handle add user button click"""
        # Verificar se xrdp está instalado
        if not self.system_deps.is_xrdp_ready():
            # Mostrar dialog informando que precisa instalar xrdp
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="xrdp não está instalado",
                body="Você precisa instalar o servidor xrdp antes de criar usuários RDP.\n\nDeseja instalar agora?"
            )
            dialog.add_response("cancel", "Cancelar")
            dialog.add_response("install", "Instalar xrdp")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", self.on_add_user_xrdp_check_response)
            dialog.present()
            return

        dialog = UserDialog(
            parent=self,
            user_manager=self.user_manager,
            rdp_config=self.rdp_config,
            de_installer=self.de_installer
        )

        dialog.connect('user-created', lambda d: self.load_users())
        dialog.present(self)

    def on_add_user_xrdp_check_response(self, dialog, response):
        """Handle response from xrdp check dialog"""
        if response == "install":
            app = self.get_application()
            if app:
                app.show_xrdp_install_dialog()

    def on_user_toggle(self, username, new_state, switch):
        """Handle user enable/disable toggle"""
        # Bloquear mudança automática do switch - vamos controlar manualmente
        # Retornar True significa "bloquear a mudança padrão"

        def do_toggle():
            """Executar a operação em thread separada"""
            try:
                if new_state:
                    # Habilitar usuário
                    success = self.user_manager.unlock_user(username)
                    if success:
                        GLib.idle_add(self.show_toast, f"✓ Usuário {username} habilitado")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, True)
                        # Atualizar lista de usuários
                        GLib.timeout_add(300, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"✗ Erro ao habilitar {username}")
                else:
                    # Desabilitar usuário
                    success = self.user_manager.lock_user(username)
                    if success:
                        GLib.idle_add(self.show_toast, f"✓ Usuário {username} desabilitado")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, False)
                        # Atualizar lista de usuários
                        GLib.timeout_add(300, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"✗ Erro ao desabilitar {username}")

            except Exception as e:
                logger.error(f"Error toggling user {username}: {e}")
                GLib.idle_add(self.show_toast, f"✗ Erro ao alterar status de {username}")

        # Executar em thread para não bloquear a UI
        import threading
        thread = threading.Thread(target=do_toggle)
        thread.daemon = True
        thread.start()

        # Retornar True para impedir mudança automática do switch
        # (vamos controlar manualmente após sucesso da operação)
        return True

    def on_delete_user(self, username):
        """Handle delete user"""
        # Verificar se usuário tem processos ativos
        active_pids = self.user_manager.get_user_processes(username)

        if active_pids:
            # Usuário tem sessão ativa - mostrar aviso
            is_connected = self.session_monitor.is_user_connected(username)
            session_info = " está conectado via RDP" if is_connected else f" tem {len(active_pids)} processos ativos"

            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"⚠ {username} está ativo",
                body=f"O usuário {username}{session_info}.\n\nPara remover o usuário, suas sessões serão encerradas automaticamente.\n\nDeseja continuar?"
            )

            dialog.add_response("cancel", "Cancelar")
            dialog.add_response("delete", "Encerrar e Remover")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            dialog.connect("response", lambda d, r: self.confirm_delete_user(username, r))
            dialog.present()
        else:
            # Usuário não tem processos ativos - confirmação normal
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"Remover {username}?",
                body="Esta ação não pode ser desfeita. Todos os dados do usuário serão removidos:\n\n• Conta de usuário\n• Diretório home (/opt/rdp-users/...)\n• Configurações RDP\n• Arquivos pessoais"
            )

            dialog.add_response("cancel", "Cancelar")
            dialog.add_response("delete", "Remover")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            dialog.connect("response", lambda d, r: self.confirm_delete_user(username, r))
            dialog.present()

    def confirm_delete_user(self, username, response):
        """Confirm user deletion"""
        if response == "delete":
            try:
                # Verificar se há processos ativos
                active_pids = self.user_manager.get_user_processes(username)

                if active_pids:
                    self.show_toast(f"Encerrando sessões de {username}...")
                    logger.info(f"User {username} has {len(active_pids)} active processes, will be killed")
                else:
                    self.show_toast(f"Removendo usuário {username}...")

                # Deletar usuário (vai matar processos automaticamente)
                success = self.user_manager.delete_user(username, remove_home=True, kill_processes=True)

                if success:
                    self.load_users()
                    self.show_toast(f"✓ Usuário {username} removido com sucesso")
                    logger.info(f"User {username} deleted successfully")
                else:
                    self.show_toast(f"✗ Erro ao remover {username}")
                    # Show error dialog
                    error_dialog = Adw.MessageDialog(
                        transient_for=self,
                        heading="Erro ao remover usuário",
                        body=f"Não foi possível remover o usuário {username}. Verifique se você tem permissões de administrador."
                    )
                    error_dialog.add_response("ok", "OK")
                    error_dialog.present()
            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                # Mostrar erro detalhado
                error_dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading="Erro ao remover usuário",
                    body=f"Não foi possível remover o usuário {username}.\n\nErro: {str(e)}"
                )
                error_dialog.add_response("ok", "OK")
                error_dialog.present()

    def on_connect_rdp(self, user):
        """Connect to RDP session"""
        ip = self.session_monitor.get_ip_address()
        connection_string = f"{ip}:{user.rdp_port}"

        # Copiar para clipboard
        clipboard = self.get_clipboard()
        clipboard.set(connection_string)

        # Determinar comando FreeRDP
        freerdp_cmd = self.system_deps.get_freerdp_command() or 'xfreerdp'

        # Mostrar dialog com informações
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Conectar ao usuário {user.username}",
            body=f"""Endereço de conexão (copiado para clipboard):

{connection_string}

Usuário: {user.username}
Desktop: {user.desktop_env.upper()}
Porta: {user.rdp_port}

Use um cliente RDP para conectar:
• Linux: {freerdp_cmd} /v:{connection_string} /u:{user.username}
• Windows: mstsc.exe /v:{connection_string}"""
        )
        dialog.add_response("ok", "OK")
        dialog.add_response("connect", "Abrir FreeRDP")
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda d, r: self.handle_connect_response(r, user))
        dialog.present()

    def handle_connect_response(self, response, user):
        """Handle connect dialog response"""
        if response == "connect":
            # Verificar se FreeRDP está instalado
            if not self.system_deps.is_freerdp_installed():
                # Mostrar dialog para instalar FreeRDP
                install_dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading="FreeRDP não está instalado",
                    body="O cliente FreeRDP é necessário para conectar a sessões RDP.\n\nDeseja instalar agora?"
                )
                install_dialog.add_response("cancel", "Cancelar")
                install_dialog.add_response("install", "Instalar FreeRDP")
                install_dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
                install_dialog.connect("response", lambda d, r: self.on_freerdp_install_response(r, user))
                install_dialog.present()
                return

            # Mostrar dialog para pedir senha
            self.show_password_dialog(user)

    def on_freerdp_install_response(self, response, user):
        """Handle FreeRDP installation response"""
        if response == "install":
            # Chamar método da aplicação para instalar FreeRDP
            app = self.get_application()
            if app:
                app.install_freerdp_with_progress()

    def show_password_dialog(self, user):
        """Show password dialog before connecting"""
        # Create dialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Conectar a {user.username}",
            body=f"Digite as credenciais para conectar via RDP."
        )

        # Create credentials entry container
        creds_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        creds_box.set_margin_top(12)
        creds_box.set_margin_bottom(12)
        creds_box.set_margin_start(12)
        creds_box.set_margin_end(12)

        # Domain field (opcional)
        domain_label = Gtk.Label(label="Domínio (opcional):")
        domain_label.set_halign(Gtk.Align.START)
        creds_box.append(domain_label)

        domain_entry = Gtk.Entry()
        domain_entry.set_hexpand(True)
        domain_entry.set_can_focus(True)
        creds_box.append(domain_entry)

        # Password field
        password_label = Gtk.Label(label="Senha:")
        password_label.set_halign(Gtk.Align.START)
        password_label.set_margin_top(8)
        creds_box.append(password_label)

        # Usar Entry com visibility=False em vez de PasswordEntry
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)  # Ocultar texto
        password_entry.set_invisible_char('•')  # Caractere para senha
        password_entry.set_hexpand(True)
        password_entry.set_can_focus(True)

        # Conectar Enter em ambos os campos para ativar botão padrão
        domain_entry.connect('activate', lambda e: password_entry.grab_focus())
        password_entry.connect('activate', lambda e: dialog.response('connect'))

        creds_box.append(password_entry)

        dialog.set_extra_child(creds_box)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("connect", "Conectar")
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("connect")
        dialog.set_close_response("cancel")

        # Store entry references
        dialog._domain_entry = domain_entry
        dialog._password_entry = password_entry

        dialog.connect("response", lambda d, r: self.on_password_dialog_response(d, r, user))
        dialog.present()

    def on_password_dialog_response(self, dialog, response, user):
        """Handle password dialog response"""
        if response == "connect":
            password = dialog._password_entry.get_text()
            domain = dialog._domain_entry.get_text().strip()

            if not password:
                self.show_toast("✗ Senha não pode estar vazia")
                return

            # Launch FreeRDP with credentials
            self.launch_freerdp_client(user, password, domain)

    def launch_freerdp_client(self, user, password=None, domain=None):
        """Launch FreeRDP client to connect to user"""
        try:
            # Obter o comando FreeRDP correto
            freerdp_cmd = self.system_deps.get_freerdp_command()
            if not freerdp_cmd:
                self.show_toast("✗ FreeRDP não encontrado")
                logger.error("FreeRDP command not found")
                return

            ip = self.session_monitor.get_ip_address()

            # Construir comando
            cmd = [
                freerdp_cmd,
                f'/v:{ip}:{user.rdp_port}',
                f'/u:{user.username}',
                '/cert:ignore',
                '/dynamic-resolution',
                '+clipboard',
                '/audio-mode:0',  # Redirect audio
                '/bpp:32',  # Color depth
            ]

            # Adicionar domínio se fornecido
            if domain:
                cmd.append(f'/d:{domain}')

            if password:
                # Passar senha via parâmetro /p: (mais simples e funciona melhor)
                cmd.append(f'/p:{password}')

                # Abrir processo normalmente
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Sem senha, abrir normalmente (vai pedir no GUI do FreeRDP)
                subprocess.Popen(cmd)

            domain_info = f" (domínio: {domain})" if domain else ""
            self.show_toast(f"Abrindo {freerdp_cmd}{domain_info}...")
            logger.info(f"Launched {freerdp_cmd} for user {user.username}{domain_info}")
        except FileNotFoundError:
            self.show_toast("✗ FreeRDP não encontrado")
            logger.error("FreeRDP command not found")
        except Exception as e:
            logger.error(f"Error launching FreeRDP: {e}")
            self.show_toast(f"✗ Erro ao abrir FreeRDP: {e}")

    def on_copy_ip(self, button):
        """Copy IP to clipboard"""
        ip = self.session_monitor.get_ip_address()

        clipboard = self.get_clipboard()
        clipboard.set(ip)

        self.show_toast(f"✓ IP {ip} copiado!")
        logger.info(f"IP {ip} copied to clipboard")

    def show_toast(self, message):
        """Show toast notification"""
        toast = Adw.Toast(title=message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def on_search_changed(self, entry):
        """Handle search text change"""
        search_text = entry.get_text().lower()

        # Filter users listbox
        self.users_listbox.set_filter_func(lambda row: self.filter_user_row(row, search_text))

    def filter_user_row(self, row, search_text):
        """Filter function for user rows"""
        if not search_text:
            return True

        title = row.get_title().lower()
        return search_text in title
