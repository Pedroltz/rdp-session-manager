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
import time
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

        # Flag para evitar atualizações simultâneas
        self._updating_users = False

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

        # Get active sessions count (apenas usuários habilitados)
        all_sessions = self.session_monitor.get_active_sessions()
        enabled_users = [u.username for u in self.user_manager.list_users() if u.enabled]
        sessions_count = sum(1 for session in all_sessions if session.username in enabled_users)
        self.sessions_row.set_subtitle(f"{sessions_count} sessões ativas")

    def update_sessions_info(self):
        """Update sessions information periodically"""
        try:
            # Contar apenas sessões de usuários habilitados
            all_sessions = self.session_monitor.get_active_sessions()
            enabled_users = [u.username for u in self.user_manager.list_users() if u.enabled]

            # Filtrar sessões de usuários habilitados
            sessions_count = sum(1 for session in all_sessions if session.username in enabled_users)

            self.sessions_row.set_subtitle(f"{sessions_count} sessões ativas")

        except Exception as e:
            logger.error(f"Error updating sessions: {e}")

        return True  # Continue timeout

    def load_users(self):
        """Load and display users"""
        # Evitar múltiplas atualizações simultâneas
        if self._updating_users:
            return

        self._updating_users = True

        try:
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
        finally:
            self._updating_users = False

    def create_user_row(self, user):
        """Create a user row widget"""
        # Check if user is connected
        is_active = self.session_monitor.is_user_connected(user.username)

        # Create row
        row = Adw.ActionRow()
        row.set_title(user.username)

        # Subtitle diferente para RemoteApp vs Desktop
        if hasattr(user, 'session_type') and user.session_type == 'remoteapp':
            app_name = user.app_command.split('/')[-1] if user.app_command else 'unknown'
            row.set_subtitle(f"RemoteApp: {app_name} • Porta {user.rdp_port} • IP: {self.session_monitor.get_ip_address()}")
        else:
            row.set_subtitle(f"{user.desktop_env.upper()} • Porta {user.rdp_port} • IP: {self.session_monitor.get_ip_address()}")

        # Status label and switch
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Status label - prioridade: 1) Desabilitado, 2) Conectado, 3) Habilitado
        if not user.enabled:
            status_text = 'Desabilitado'
        elif is_active:
            status_text = 'Conectado'
        else:
            status_text = 'Habilitado'

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

        # Menu button (...)
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name('view-more-symbolic')
        menu_button.add_css_class('flat')
        menu_button.set_valign(Gtk.Align.CENTER)
        menu_button.set_tooltip_text('Opções de gerenciamento')

        # Create popover menu
        popover = Gtk.Popover()
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        menu_box.set_margin_top(6)
        menu_box.set_margin_bottom(6)
        menu_box.set_margin_start(6)
        menu_box.set_margin_end(6)

        # Superuser toggle row
        sudo_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sudo_row.set_margin_top(6)
        sudo_row.set_margin_bottom(6)
        sudo_row.set_margin_start(12)
        sudo_row.set_margin_end(12)

        sudo_label = Gtk.Label(label="Superusuário")
        sudo_label.set_halign(Gtk.Align.START)
        sudo_label.set_hexpand(True)

        sudo_switch = Gtk.Switch()
        sudo_switch.set_active(user.is_superuser)
        sudo_switch.set_valign(Gtk.Align.CENTER)
        sudo_switch.set_tooltip_text('Conceder/revogar privilégios sudo')
        sudo_switch.connect('state-set', lambda s, state: self.on_sudo_toggle(user.username, state, s))

        sudo_row.append(sudo_label)
        sudo_row.append(sudo_switch)

        menu_box.append(sudo_row)

        # Settings row (configurações de usuário)
        settings_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        settings_row.set_margin_top(6)
        settings_row.set_margin_bottom(6)
        settings_row.set_margin_start(12)
        settings_row.set_margin_end(12)

        settings_label = Gtk.Label(label="Configurações de Usuário")
        settings_label.set_halign(Gtk.Align.START)
        settings_label.set_hexpand(True)

        settings_icon = Gtk.Image.new_from_icon_name("emblem-system-symbolic")

        settings_row.append(settings_label)
        settings_row.append(settings_icon)

        # Tornar a row clicável usando GestureClick
        settings_gesture = Gtk.GestureClick.new()
        settings_gesture.connect("released", lambda g, n, x, y: self.on_user_settings(user, popover))
        settings_row.add_controller(settings_gesture)

        # Adicionar estilo hover
        settings_row.set_cursor_from_name("pointer")

        menu_box.append(settings_row)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)
        separator.set_margin_bottom(6)
        menu_box.append(separator)

        # Copy IP row (estilo igual ao de cima, sem Button)
        copy_ip_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        copy_ip_row.set_margin_top(6)
        copy_ip_row.set_margin_bottom(6)
        copy_ip_row.set_margin_start(12)
        copy_ip_row.set_margin_end(12)

        copy_ip_label = Gtk.Label(label="Copiar IP + Porta")
        copy_ip_label.set_halign(Gtk.Align.START)
        copy_ip_label.set_hexpand(True)

        copy_ip_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")

        copy_ip_row.append(copy_ip_label)
        copy_ip_row.append(copy_ip_icon)

        # Tornar a row clicável usando GestureClick
        gesture = Gtk.GestureClick.new()
        gesture.connect("released", lambda g, n, x, y: self.on_copy_user_ip(user, popover))
        copy_ip_row.add_controller(gesture)

        # Adicionar estilo hover
        copy_ip_row.set_cursor_from_name("pointer")

        menu_box.append(copy_ip_row)
        popover.set_child(menu_box)
        menu_button.set_popover(popover)

        status_box.append(menu_button)

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

    def on_sudo_toggle(self, username, new_state, switch):
        """Handle sudo privilege toggle"""
        # Bloquear mudança automática do switch - vamos controlar manualmente

        # Verificar se usuário tem sessão ativa
        is_connected = self.session_monitor.is_user_connected(username)
        has_processes = len(self.user_manager.get_user_processes(username)) > 0

        if is_connected or has_processes:
            # Mostrar aviso sobre reconexão necessária
            action_text = "conceder" if new_state else "revogar"
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"⚠ {username} está conectado",
                body=f"""Para {action_text} privilégios sudo, a sessão do usuário será encerrada automaticamente.

⚠ IMPORTANTE: Mudanças de grupo só têm efeito após logout/login completo.

O usuário precisará reconectar via RDP para que os privilégios {"de superusuário sejam aplicados" if new_state else "sejam removidos"}.

Deseja continuar?"""
            )
            dialog.add_response("cancel", "Cancelar")
            dialog.add_response("continue", "Continuar e Encerrar Sessão")
            dialog.set_response_appearance("continue", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("continue")
            dialog.set_close_response("cancel")

            # Store data for callback
            dialog._username = username
            dialog._new_state = new_state
            dialog._switch = switch

            dialog.connect("response", self.on_sudo_confirm_response)
            dialog.present()
        else:
            # Sem sessão ativa, executar diretamente
            self._do_sudo_toggle(username, new_state, switch)

        # Retornar True para impedir mudança automática do switch
        return True

    def on_sudo_confirm_response(self, dialog, response):
        """Handle sudo confirmation dialog response"""
        if response == "continue":
            self._do_sudo_toggle(dialog._username, dialog._new_state, dialog._switch)

    def _do_sudo_toggle(self, username, new_state, switch):
        """Execute sudo toggle operation"""
        def do_toggle():
            """Executar a operação em thread separada"""
            try:
                if new_state:
                    # Conceder privilégios sudo
                    success = self.user_manager.grant_sudo(username, kill_sessions=True)
                    if success:
                        GLib.idle_add(self.show_toast, f"✓ Privilégios sudo concedidos - Reconecte para aplicar")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, True)
                        # Atualizar lista de usuários
                        GLib.timeout_add(500, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"✗ Erro ao conceder privilégios sudo para {username}")
                else:
                    # Revogar privilégios sudo
                    success = self.user_manager.revoke_sudo(username, kill_sessions=True)
                    if success:
                        GLib.idle_add(self.show_toast, f"✓ Privilégios sudo revogados - Reconecte para aplicar")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, False)
                        # Atualizar lista de usuários
                        GLib.timeout_add(500, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"✗ Erro ao revogar privilégios sudo de {username}")

            except Exception as e:
                logger.error(f"Error toggling sudo for user {username}: {e}")
                GLib.idle_add(self.show_toast, f"✗ Erro ao alterar privilégios sudo de {username}")

        # Executar em thread para não bloquear a UI
        import threading
        thread = threading.Thread(target=do_toggle)
        thread.daemon = True
        thread.start()

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

        # Ir direto para dialog de senha
        self.show_password_dialog(user)

    def on_freerdp_install_response(self, response, user):
        """Handle FreeRDP installation response"""
        if response == "install":
            # Chamar método da aplicação para instalar FreeRDP
            app = self.get_application()
            if app:
                app.install_freerdp_with_progress()

    def on_user_settings(self, user, popover):
        """Open user settings dialog"""
        # Fechar o popover
        popover.popdown()

        # Criar dialog de configurações
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Configurações de {user.username}",
            body="Altere as informações do usuário:"
        )

        # Criar container para os campos
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        settings_box.set_margin_top(12)
        settings_box.set_margin_bottom(12)
        settings_box.set_margin_start(12)
        settings_box.set_margin_end(12)

        # Campo: Nome de usuário
        username_label = Gtk.Label(label="Nome de usuário:")
        username_label.set_halign(Gtk.Align.START)
        settings_box.append(username_label)

        username_entry = Gtk.Entry()
        username_entry.set_text(user.username)
        username_entry.set_hexpand(True)
        settings_box.append(username_entry)

        # Campo: Nome completo
        fullname_label = Gtk.Label(label="Nome completo:")
        fullname_label.set_halign(Gtk.Align.START)
        fullname_label.set_margin_top(8)
        settings_box.append(fullname_label)

        # Obter nome completo atual
        try:
            import pwd
            user_info = pwd.getpwnam(user.username)
            current_fullname = user_info.pw_gecos.split(',')[0] if user_info.pw_gecos else ""
        except:
            current_fullname = ""

        fullname_entry = Gtk.Entry()
        fullname_entry.set_text(current_fullname)
        fullname_entry.set_hexpand(True)
        settings_box.append(fullname_entry)

        # Separator
        separator1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator1.set_margin_top(12)
        separator1.set_margin_bottom(8)
        settings_box.append(separator1)

        # Campo: Tipo de Sessão
        session_type_label = Gtk.Label(label="Tipo de Sessão:")
        session_type_label.set_halign(Gtk.Align.START)
        settings_box.append(session_type_label)

        session_type_combo = Gtk.ComboBoxText()
        session_type_combo.append("desktop", "Desktop Completo")
        session_type_combo.append("remoteapp", "RemoteApp (Aplicativo Único)")

        # Set current value
        current_session_type = getattr(user, 'session_type', 'desktop')
        session_type_combo.set_active_id(current_session_type)
        settings_box.append(session_type_combo)

        # Campo: Comando do Aplicativo (para RemoteApp)
        app_label = Gtk.Label(label="Comando do Aplicativo:")
        app_label.set_halign(Gtk.Align.START)
        app_label.set_margin_top(8)
        settings_box.append(app_label)

        # Campo de entrada para comando personalizado
        custom_app_entry = Gtk.Entry()
        custom_app_entry.set_hexpand(True)
        custom_app_entry.set_placeholder_text("Ex: firefox, thunderbird, libreoffice...")
        if current_session_type == 'remoteapp' and hasattr(user, 'app_command'):
            custom_app_entry.set_text(user.app_command)
        settings_box.append(custom_app_entry)

        # Campo: Argumentos
        app_args_entry = Gtk.Entry()
        app_args_entry.set_hexpand(True)
        app_args_entry.set_placeholder_text("Argumentos (opcional)...")
        if current_session_type == 'remoteapp' and hasattr(user, 'app_args'):
            app_args_entry.set_text(user.app_args)
        settings_box.append(app_args_entry)

        # Função para toggle visibility based on session type
        def on_session_type_changed(combo):
            is_remoteapp = combo.get_active_id() == 'remoteapp'
            app_label.set_visible(is_remoteapp)
            custom_app_entry.set_visible(is_remoteapp)
            app_args_entry.set_visible(is_remoteapp)

        session_type_combo.connect('changed', on_session_type_changed)

        # Initialize visibility
        on_session_type_changed(session_type_combo)

        # Separator
        separator2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator2.set_margin_top(12)
        separator2.set_margin_bottom(8)
        settings_box.append(separator2)

        # Campo: Nova senha
        password_label = Gtk.Label(label="Nova senha (deixe em branco para não alterar):")
        password_label.set_halign(Gtk.Align.START)
        password_label.set_margin_top(8)
        settings_box.append(password_label)

        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_entry.set_invisible_char('•')
        password_entry.set_hexpand(True)
        password_entry.set_placeholder_text("Digite a nova senha ou deixe vazio")
        settings_box.append(password_entry)

        # Confirmação de senha
        confirm_label = Gtk.Label(label="Confirmar senha:")
        confirm_label.set_halign(Gtk.Align.START)
        confirm_label.set_margin_top(4)
        settings_box.append(confirm_label)

        confirm_entry = Gtk.Entry()
        confirm_entry.set_visibility(False)
        confirm_entry.set_invisible_char('•')
        confirm_entry.set_hexpand(True)
        settings_box.append(confirm_entry)

        dialog.set_extra_child(settings_box)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("save", "Salvar Alterações")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        # Store references
        dialog._user = user
        dialog._username_entry = username_entry
        dialog._fullname_entry = fullname_entry
        dialog._session_type_combo = session_type_combo
        dialog._custom_app_entry = custom_app_entry
        dialog._app_args_entry = app_args_entry
        dialog._password_entry = password_entry
        dialog._confirm_entry = confirm_entry
        dialog._original_username = user.username

        dialog.connect("response", self.on_user_settings_response)
        dialog.present()

    def on_user_settings_response(self, dialog, response):
        """Handle user settings dialog response"""
        if response == "save":
            new_username = dialog._username_entry.get_text().strip()
            new_fullname = dialog._fullname_entry.get_text().strip()
            new_session_type = dialog._session_type_combo.get_active_id()
            new_password = dialog._password_entry.get_text()
            confirm_password = dialog._confirm_entry.get_text()
            original_username = dialog._original_username
            original_session_type = getattr(dialog._user, 'session_type', 'desktop')

            # Get RemoteApp data
            new_app_command = ''
            new_app_args = ''
            if new_session_type == 'remoteapp':
                # Pegar comando direto do campo de entrada
                new_app_command = dialog._custom_app_entry.get_text().strip()
                new_app_args = dialog._app_args_entry.get_text().strip()

                # Validar que app command não está vazio
                if not new_app_command:
                    self.show_toast("✗ Comando do aplicativo não pode estar vazio para RemoteApp")
                    return

            # Validar dados
            if not new_username:
                self.show_toast("✗ Nome de usuário não pode estar vazio")
                return

            # Validar senha se fornecida
            if new_password or confirm_password:
                if new_password != confirm_password:
                    self.show_toast("✗ As senhas não coincidem")
                    return
                if len(new_password) < 6:
                    self.show_toast("✗ Senha deve ter pelo menos 6 caracteres")
                    return

            # Aplicar alterações em thread separada
            def apply_changes():
                try:
                    changes_made = []

                    # Obter nome completo original
                    try:
                        import pwd
                        user_info = pwd.getpwnam(original_username)
                        original_fullname = user_info.pw_gecos.split(',')[0] if user_info.pw_gecos else ""
                    except:
                        original_fullname = ""

                    # 1. Alterar nome completo (se mudou)
                    if new_fullname and new_fullname != original_fullname:
                        success = self.user_manager.change_user_fullname(original_username, new_fullname)
                        if success:
                            changes_made.append("nome completo")
                        else:
                            GLib.idle_add(self.show_toast, "✗ Erro ao alterar nome completo")
                            return

                    # 2. Alterar senha (se fornecida)
                    if new_password:
                        success = self.user_manager.change_password(original_username, new_password)
                        if success:
                            changes_made.append("senha")
                        else:
                            GLib.idle_add(self.show_toast, "✗ Erro ao alterar senha")
                            return

                    # 3. Alterar tipo de sessão (se mudou)
                    if new_session_type != original_session_type:
                        # Determinar comando correto
                        if new_session_type == 'remoteapp':
                            session_command = new_app_command
                            session_args = new_app_args
                        else:
                            # Para desktop, usar o DE atual do usuário
                            user_obj = self.user_manager.get_user(original_username)
                            if user_obj and user_obj.desktop_env != 'remoteapp':
                                # Mapear DE para comando
                                de_commands = {
                                    'xfce': 'startxfce4',
                                    'gnome': 'gnome-session',
                                    'kde': 'startplasma-x11',
                                    'mate': 'mate-session',
                                    'cinnamon': 'cinnamon-session',
                                    'lxde': 'startlxde',
                                    'lxqt': 'startlxqt'
                                }
                                session_command = de_commands.get(user_obj.desktop_env, 'startxfce4')
                            else:
                                session_command = 'startxfce4'  # Default
                            session_args = ''

                        success = self.user_manager.change_user_session_type(
                            original_username, new_session_type, session_command, session_args
                        )
                        if success:
                            changes_made.append("tipo de sessão")
                        else:
                            GLib.idle_add(self.show_toast, "✗ Erro ao alterar tipo de sessão")
                            return
                    elif new_session_type == 'remoteapp':
                        # Mesmo tipo, mas pode ter mudado app/args
                        original_app = getattr(dialog._user, 'app_command', '')
                        original_args = getattr(dialog._user, 'app_args', '')

                        if new_app_command != original_app or new_app_args != original_args:
                            success = self.user_manager.change_user_session_type(
                                original_username, 'remoteapp', new_app_command, new_app_args
                            )
                            if success:
                                changes_made.append("aplicativo RemoteApp")
                            else:
                                GLib.idle_add(self.show_toast, "✗ Erro ao alterar aplicativo")
                                return

                    # 4. Renomear usuário (último, pois muda o username)
                    if new_username != original_username:
                        success = self.user_manager.rename_user(original_username, new_username)
                        if success:
                            changes_made.append("nome de usuário")
                        else:
                            GLib.idle_add(self.show_toast, f"✗ Erro ao renomear usuário")
                            return

                    # Mostrar sucesso
                    if changes_made:
                        changes_text = ", ".join(changes_made)
                        GLib.idle_add(self.show_toast, f"✓ Alterado: {changes_text}")
                        GLib.timeout_add(300, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, "ℹ Nenhuma alteração foi feita")

                except Exception as e:
                    logger.error(f"Error updating user settings: {e}")
                    GLib.idle_add(self.show_toast, f"✗ Erro ao atualizar configurações")

            # Executar em thread
            import threading
            thread = threading.Thread(target=apply_changes)
            thread.daemon = True
            thread.start()

    def on_copy_user_ip(self, user, popover):
        """Copy user connection string to clipboard"""
        ip = self.session_monitor.get_ip_address()
        connection_string = f"{ip}:{user.rdp_port}"

        clipboard = self.get_clipboard()
        clipboard.set(connection_string)

        self.show_toast(f"✓ {connection_string} copiado!")

        # Fechar o popover
        popover.popdown()

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

            # Fechar diálogo antes de abrir FreeRDP
            dialog.close()

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

            # Verificar se é RemoteApp para ajustar parâmetros
            is_remoteapp = hasattr(user, 'session_type') and user.session_type == 'remoteapp'

            # Construir comando base
            cmd = [
                freerdp_cmd,
                f'/v:{ip}:{user.rdp_port}',
                f'/u:{user.username}',
                '/cert:ignore',
                '+clipboard',
                '/audio-mode:0',  # Redirect audio
                '/bpp:32',  # Color depth
            ]

            # Para RemoteApp e Desktop, sempre usar dynamic-resolution
            cmd.append('/dynamic-resolution')

            if is_remoteapp:
                app_full_cmd = f"{user.app_command} {user.app_args}".strip()
                logger.info(f"Launching RemoteApp: {app_full_cmd}")

            # Adicionar domínio se fornecido
            if domain:
                cmd.append(f'/d:{domain}')

            if password:
                cmd.append(f'/p:{password}')

            # Log do comando completo (ocultando senha)
            cmd_display = [arg if not arg.startswith('/p:') else '/p:***' for arg in cmd]
            logger.info(f"FreeRDP command: {' '.join(cmd_display)}")

            # Abrir processo com captura de erro
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Verificar se processo iniciou corretamente
            time.sleep(0.5)
            if process.poll() is not None:
                # Processo terminou imediatamente - houve erro
                _, stderr = process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else ''
                logger.error(f"FreeRDP failed. Exit code: {process.returncode}, Error: {error_msg}")
                raise Exception(f"FreeRDP terminou com código {process.returncode}: {error_msg[:200]}")

            # Mostrar mensagem de sucesso
            is_remoteapp = hasattr(user, 'session_type') and user.session_type == 'remoteapp'
            if is_remoteapp:
                app_name = user.app_command.split('/')[-1]
                self.show_toast(f"Abrindo RemoteApp: {app_name}...")
                logger.info(f"Launched RemoteApp {app_name} for user {user.username}")
            else:
                domain_suffix = f" (domínio: {domain})" if domain else ""
                self.show_toast(f"Abrindo {freerdp_cmd}{domain_suffix}...")
                logger.info(f"Launched {freerdp_cmd} for user {user.username}{domain_suffix}")
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
