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
        self.sessions_row.set_subtitle(f"{sessions_count} active sessions")

    def update_sessions_info(self):
        """Update sessions information periodically"""
        try:
            # Contar apenas sessões de usuários habilitados
            all_sessions = self.session_monitor.get_active_sessions()
            enabled_users = [u.username for u in self.user_manager.list_users() if u.enabled]

            # Filtrar sessões de usuários habilitados
            sessions_count = sum(1 for session in all_sessions if session.username in enabled_users)

            self.sessions_row.set_subtitle(f"{sessions_count} active sessions")

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
            row.set_subtitle(f"RemoteApp: {app_name} • Port {user.rdp_port} • IP: {self.session_monitor.get_ip_address()}")
        else:
            row.set_subtitle(f"{user.desktop_env.upper()} • Port {user.rdp_port} • IP: {self.session_monitor.get_ip_address()}")

        # Status label and switch
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Status label - prioridade: 1) Desabilitado, 2) Conectado, 3) Habilitado
        if not user.enabled:
            status_text = 'Disabled'
        elif is_active:
            status_text = 'Connected'
        else:
            status_text = 'Enabled'

        status_label = Gtk.Label(label=status_text)
        status_label.add_css_class('dim-label')
        status_label.set_margin_end(12)  # Espaço antes do switch

        status_box.append(status_label)

        # Enable/Disable Switch (à direita do status)
        enable_switch = Gtk.Switch()
        enable_switch.set_active(user.enabled)
        enable_switch.set_valign(Gtk.Align.CENTER)
        enable_switch.set_tooltip_text('Enable/disable user')
        enable_switch.connect('state-set', lambda s, state: self.on_user_toggle(user.username, state, s))
        status_box.append(enable_switch)

        # Menu button (...)
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name('view-more-symbolic')
        menu_button.add_css_class('flat')
        menu_button.set_valign(Gtk.Align.CENTER)
        menu_button.set_tooltip_text('Management options')

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

        sudo_label = Gtk.Label(label="Superuser")
        sudo_label.set_halign(Gtk.Align.START)
        sudo_label.set_hexpand(True)

        sudo_switch = Gtk.Switch()
        sudo_switch.set_active(user.is_superuser)
        sudo_switch.set_valign(Gtk.Align.CENTER)
        sudo_switch.set_tooltip_text('Grant/revoke sudo privileges')
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

        settings_label = Gtk.Label(label="User Settings")
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

        copy_ip_label = Gtk.Label(label="Copy IP + Port")
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
        connect_btn.set_tooltip_text('Connect via RDP')
        connect_btn.connect('clicked', lambda b: self.on_connect_rdp(user))

        # Delete button
        delete_btn = Gtk.Button(icon_name='user-trash-symbolic')
        delete_btn.add_css_class('flat')
        delete_btn.add_css_class('destructive-action')
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.set_tooltip_text('Remove user')
        delete_btn.connect('clicked', lambda b: self.on_delete_user(user.username))

        button_box.append(connect_btn)
        button_box.append(delete_btn)
        row.add_suffix(button_box)

        return row

    def create_xrdp_warning_banner(self):
        """Create warning banner for missing xrdp"""
        if not hasattr(Adw, "Banner"):
            logger.info("The installed libadwaita does not provide Adw.Banner.")
            return

        # Criar Banner
        self.xrdp_banner = Adw.Banner()
        self.xrdp_banner.set_title("WARNING xrdp server is not installed—the application will not work without it")
        self.xrdp_banner.set_button_label("Install Now")
        self.xrdp_banner.connect('button-clicked', self.on_install_xrdp_clicked)
        self.xrdp_banner.set_revealed(False)

        content = self.toast_overlay.get_child()
        if content and isinstance(content, Gtk.Box):
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
            tooltip = "Install xrdp before creating RDP users"
            self.add_user_button.set_tooltip_text(tooltip)
            self.empty_add_user_button.set_tooltip_text(tooltip)
        else:
            self.add_user_button.set_tooltip_text("Add a new RDP user")
            self.empty_add_user_button.set_tooltip_text("Add a new RDP user")

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
                heading="xrdp Is Not Installed",
                body="You must install the xrdp server before creating RDP users.\n\nWould you like to install it now?"
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("install", "Install xrdp")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", self.on_add_user_xrdp_check_response)
            dialog.present()
            return

        # Adw.Dialog and the corresponding template are available only in
        # newer libadwaita versions. Loading this module on demand keeps the
        # main application compatible with older supported distributions.
        from .user_dialog import UserDialog

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
                        GLib.idle_add(self.show_toast, f"OK User {username} enabled")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, True)
                        # Atualizar lista de usuários
                        GLib.timeout_add(300, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"X Error enabling {username}")
                else:
                    # Desabilitar usuário
                    success = self.user_manager.lock_user(username)
                    if success:
                        GLib.idle_add(self.show_toast, f"OK User {username} disabled")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, False)
                        # Atualizar lista de usuários
                        GLib.timeout_add(300, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"X Error disabling {username}")

            except Exception as e:
                logger.error(f"Error toggling user {username}: {e}")
                GLib.idle_add(self.show_toast, f"X Error changing the status of {username}")

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
            action_text = "grant" if new_state else "revoke"
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"WARNING {username} is connected",
                body=f"""To {action_text} sudo privileges, the user's session will be terminated automatically.

IMPORTANT: Group changes only take effect after a complete logout and login.

The user must reconnect via RDP for the privileges to be {"applied" if new_state else "removed"}.

Would you like to continue?"""
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("continue", "Continue and End Session")
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
                        GLib.idle_add(self.show_toast, "OK Sudo privileges granted—reconnect to apply")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, True)
                        # Atualizar lista de usuários
                        GLib.timeout_add(500, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"X Error granting sudo privileges to {username}")
                else:
                    # Revogar privilégios sudo
                    success = self.user_manager.revoke_sudo(username, kill_sessions=True)
                    if success:
                        GLib.idle_add(self.show_toast, "OK Sudo privileges revoked—reconnect to apply")
                        # Atualizar o switch manualmente
                        GLib.idle_add(switch.set_active, False)
                        # Atualizar lista de usuários
                        GLib.timeout_add(500, self.load_users)
                    else:
                        GLib.idle_add(self.show_toast, f"X Error revoking sudo privileges from {username}")

            except Exception as e:
                logger.error(f"Error toggling sudo for user {username}: {e}")
                GLib.idle_add(self.show_toast, f"X Error changing sudo privileges for {username}")

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
            session_info = " is connected through RDP" if is_connected else f" has {len(active_pids)} active processes"

            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"WARNING {username} is active",
                body=f"User {username}{session_info}.\n\nThe user's sessions will be terminated automatically before removal.\n\nWould you like to continue?"
            )

            dialog.add_response("cancel", "Cancel")
            dialog.add_response("delete", "End Sessions and Remove")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            dialog.connect("response", lambda d, r: self.confirm_delete_user(username, r))
            dialog.present()
        else:
            # Usuário não tem processos ativos - confirmação normal
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"Remove {username}?",
                body="This action cannot be undone. All user data will be removed:\n\n• User account\n• Home directory (/opt/rdp-users/...)\n• RDP settings\n• Personal files"
            )

            dialog.add_response("cancel", "Cancel")
            dialog.add_response("delete", "Remove")
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
                    self.show_toast(f"Ending sessions for {username}...")
                    logger.info(f"User {username} has {len(active_pids)} active processes, will be killed")
                else:
                    self.show_toast(f"Removing user {username}...")

                # Deletar usuário (vai matar processos automaticamente)
                success = self.user_manager.delete_user(username, remove_home=True, kill_processes=True)

                if success:
                    self.load_users()
                    self.show_toast(f"OK User {username} removed successfully")
                    logger.info(f"User {username} deleted successfully")
                else:
                    self.show_toast(f"X Error removing {username}")
                    # Show error dialog
                    error_dialog = Adw.MessageDialog(
                        transient_for=self,
                        heading="Error Removing User",
                        body=f"User {username} could not be removed. Check that you have administrator permissions."
                    )
                    error_dialog.add_response("ok", "OK")
                    error_dialog.present()
            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                # Mostrar erro detalhado
                error_dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading="Error Removing User",
                    body=f"User {username} could not be removed.\n\nError: {str(e)}"
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
                heading="FreeRDP Is Not Installed",
                body="The FreeRDP client is required to connect to RDP sessions.\n\nWould you like to install it now?"
            )
            install_dialog.add_response("cancel", "Cancel")
            install_dialog.add_response("install", "Install FreeRDP")
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

        # Criar dialog de configurações usando Adw.Dialog (não MessageDialog) para ter controle total do tamanho
        dialog = Adw.Dialog()
        dialog.set_title("Edit RDP User")
        dialog.set_content_width(500)
        dialog.set_content_height(680)
        dialog.set_can_close(True)

        # Criar toolbar view com header bar
        toolbar_view = Adw.ToolbarView()

        # Header bar com botões
        header_bar = Adw.HeaderBar()

        # Botão Cancelar
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect('clicked', lambda b: dialog.close())
        header_bar.pack_start(cancel_button)

        # Botão Salvar
        save_button = Gtk.Button(label="Save Changes")
        save_button.add_css_class("suggested-action")
        header_bar.pack_end(save_button)

        toolbar_view.add_top_bar(header_bar)

        # Criar container principal com as mesmas dimensões da tela de criação
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)

        # Criar container para os campos
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)

        # === Banner de Status no Topo ===
        status_banner = Adw.PreferencesGroup()
        status_banner.set_title("User Information")

        # UID Row
        uid_row = Adw.ActionRow()
        uid_row.set_title("System UID")
        uid_row.set_subtitle(f"{user.uid}")
        status_banner.add(uid_row)

        # Porta RDP Row
        port_row = Adw.ActionRow()
        port_row.set_title("RDP Port")
        port_row.set_subtitle(f"{user.rdp_port}")
        status_banner.add(port_row)

        # Diretório Home Row
        home_row = Adw.ActionRow()
        home_row.set_title("Home Directory")
        home_row.set_subtitle(f"{user.home_dir}")
        status_banner.add(home_row)

        settings_box.append(status_banner)

        # === Grupo: Informações Básicas ===
        basic_info_group = Adw.PreferencesGroup()
        basic_info_group.set_title("Basic Information")
        basic_info_group.set_description("User identity and display name")

        # Campo: Nome de usuário
        username_entry = Adw.EntryRow()
        username_entry.set_title("Username")
        username_entry.set_text(user.username)
        username_entry.set_show_apply_button(False)
        basic_info_group.add(username_entry)

        # Campo: Nome completo
        # Obter nome completo atual
        try:
            import pwd
            user_info = pwd.getpwnam(user.username)
            current_fullname = user_info.pw_gecos.split(',')[0] if user_info.pw_gecos else ""
        except:
            current_fullname = ""

        fullname_entry = Adw.EntryRow()
        fullname_entry.set_title("Full Name")
        fullname_entry.set_text(current_fullname)
        fullname_entry.set_show_apply_button(False)
        basic_info_group.add(fullname_entry)

        settings_box.append(basic_info_group)

        # === Grupo: Tipo de Sessão ===
        session_group = Adw.PreferencesGroup()
        session_group.set_title("Session Type")
        session_group.set_description("Choose between a full desktop or a single application")

        # Campo: Tipo de Sessão usando AdwComboRow
        session_type_combo = Adw.ComboRow()
        session_type_combo.set_title("Connection Mode")
        # Create string list for session types
        session_string_list = Gtk.StringList()
        session_string_list.append("Full Desktop")
        session_string_list.append("RemoteApp (Linux Application)")
        session_string_list.append("WineGE RemoteApp (Windows Application)")

        session_type_combo.set_model(session_string_list)

        # Set current value (map session type to index)
        current_session_type = getattr(user, 'session_type', 'desktop')
        session_type_map = {'desktop': 0, 'remoteapp': 1, 'winege-remoteapp': 2}
        session_type_combo.set_selected(session_type_map.get(current_session_type, 0))

        session_group.add(session_type_combo)
        settings_box.append(session_group)

        # === Grupo: RemoteApp (Linux) ===
        remoteapp_group = Adw.PreferencesGroup()
        remoteapp_group.set_title("RemoteApp Linux")
        remoteapp_group.set_description("Configure the Linux application to run")

        # Campo de entrada para comando personalizado
        custom_app_entry = Adw.EntryRow()
        custom_app_entry.set_title("Application Command")
        custom_app_entry.set_show_apply_button(False)
        if current_session_type == 'remoteapp' and hasattr(user, 'app_command'):
            custom_app_entry.set_text(user.app_command)
        remoteapp_group.add(custom_app_entry)

        # Campo: Argumentos (Linux RemoteApp)
        app_args_entry = Adw.EntryRow()
        app_args_entry.set_title("Arguments (optional)")
        app_args_entry.set_show_apply_button(False)
        if current_session_type == 'remoteapp' and hasattr(user, 'app_args'):
            app_args_entry.set_text(user.app_args)
        remoteapp_group.add(app_args_entry)

        settings_box.append(remoteapp_group)

        # === Grupo: WineGE RemoteApp ===
        winege_group = Adw.PreferencesGroup()
        winege_group.set_title("Windows Application (WineGE)")
        winege_group.set_description("Configure the Windows executable to run through Wine-GE")

        # Row com botões de seleção
        winege_buttons_row = Adw.ActionRow()
        winege_buttons_row.set_title("Select File")
        winege_buttons_row.set_subtitle("Choose the .exe file from your computer")
        # Box horizontal para botões
        winege_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        winege_buttons_box.set_valign(Gtk.Align.CENTER)

        # Botão para selecionar .exe
        winege_select_button = Gtk.Button()
        winege_select_button.set_label("Select")
        winege_select_button.add_css_class("suggested-action")

        def on_select_winege_exe(btn):
            """File picker for .exe - hide dialog temporarily to allow GTK4 file picker"""
            logger.info("=== WineGE 'Select' button clicked ===")
            from gi.repository import Gio

            # Esconder o dialog de configurações temporariamente
            dialog.set_visible(False)

            # Criar file dialog GTK4
            file_dialog = Gtk.FileDialog.new()
            file_dialog.set_title("Select Windows Executable")

            # Definir diretório inicial
            user_home = f"/opt/rdp-users/{user.username}"
            try:
                if Path(user_home).exists():
                    initial_folder = Gio.File.new_for_path(user_home)
                    file_dialog.set_initial_folder(initial_folder)
                    logger.info(f"File picker will start at: {user_home}")
            except Exception as e:
                logger.warning(f"Could not set initial folder: {e}")

            # Filters
            filter_exe = Gtk.FileFilter()
            filter_exe.set_name("Windows Executables (*.exe)")
            filter_exe.add_pattern("*.exe")
            filter_exe.add_pattern("*.EXE")

            filter_all = Gtk.FileFilter()
            filter_all.set_name("Todos os arquivos")
            filter_all.add_pattern("*")

            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(filter_exe)
            filters.append(filter_all)

            file_dialog.set_filters(filters)
            file_dialog.set_default_filter(filter_exe)

            def on_file_selected(source_object, result):
                logger.info("=== File selection callback triggered ===")

                # Mostrar o dialog de configurações novamente
                dialog.set_visible(True)

                try:
                    file = source_object.open_finish(result)
                    if file:
                        # Obter caminho do arquivo
                        file_path = file.get_path()

                        # Se get_path() retornar None, tentar URI
                        if not file_path:
                            import urllib.parse
                            uri = file.get_uri()
                            file_path = urllib.parse.unquote(uri.replace('file://', ''))

                        # Garantir que o caminho é absoluto
                        if file_path and not file_path.startswith('/'):
                            file_path = '/' + file_path

                        logger.info(f"File selected: {file_path}")
                        winege_exe_entry.set_text(file_path)
                except Exception as e:
                    error_msg = str(e)
                    if "No file selected" not in error_msg and "dismissed" not in error_msg.lower():
                        logger.error(f"Error selecting file: {e}")

            # Abrir file dialog com MainWindow como parent
            file_dialog.open(self, None, on_file_selected)

        winege_select_button.connect('clicked', on_select_winege_exe)
        winege_buttons_box.append(winege_select_button)

        # Botão para listar executáveis disponíveis
        winege_list_button = Gtk.Button()
        winege_list_button.set_label("List Available")

        def on_list_winege_exes(btn):
            """Show list of available executables for the user"""
            logger.info("=== Listing available executables ===")

            # Buscar executáveis disponíveis
            executables = self.user_manager.list_user_executables(user.username)

            if not executables:
                self.show_toast("X No executables found")
                return

            # Criar dialog de seleção
            list_dialog = Adw.MessageDialog(
                transient_for=dialog,
                heading="Available Executables",
                body=f"Select the executable for {user.username}:"
            )

            # Criar listbox com executáveis
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_min_content_height(300)
            scrolled.set_min_content_width(500)

            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            listbox.add_css_class("boxed-list")

            for source, exe_path in executables:
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                box.set_margin_top(8)
                box.set_margin_bottom(8)
                box.set_margin_start(12)
                box.set_margin_end(12)

                # Nome do arquivo
                label_name = Gtk.Label()
                label_name.set_markup(f"<b>{Path(exe_path).name}</b>")
                label_name.set_halign(Gtk.Align.START)
                box.append(label_name)

                # Caminho e fonte
                label_path = Gtk.Label(label=f" {exe_path}")
                label_path.set_halign(Gtk.Align.START)
                label_path.add_css_class("dim-label")
                label_path.add_css_class("caption")
                box.append(label_path)

                label_source = Gtk.Label(label=f" {source}")
                label_source.set_halign(Gtk.Align.START)
                label_source.add_css_class("dim-label")
                label_source.add_css_class("caption")
                box.append(label_source)

                row.set_child(box)
                row.exe_path = exe_path  # Store path in row
                listbox.append(row)

            scrolled.set_child(listbox)
            list_dialog.set_extra_child(scrolled)

            list_dialog.add_response("cancel", "Cancel")
            list_dialog.add_response("select", "Select")
            list_dialog.set_response_appearance("select", Adw.ResponseAppearance.SUGGESTED)

            def on_list_dialog_response(dlg, response):
                if response == "select":
                    selected_row = listbox.get_selected_row()
                    if selected_row and hasattr(selected_row, 'exe_path'):
                        logger.info(f"Selected executable: {selected_row.exe_path}")
                        winege_exe_entry.set_text(selected_row.exe_path)
                        self.show_toast("OK Executable selected")

            list_dialog.connect('response', on_list_dialog_response)
            list_dialog.present()

        winege_list_button.connect('clicked', on_list_winege_exes)
        winege_buttons_box.append(winege_list_button)

        # Adicionar box de botões à row
        winege_buttons_row.add_suffix(winege_buttons_box)
        winege_group.add(winege_buttons_row)

        # Campo de entrada para caminho do .exe
        winege_exe_entry = Adw.EntryRow()
        winege_exe_entry.set_title("Executable Path")
        winege_exe_entry.set_show_apply_button(False)
        if current_session_type == 'winege-remoteapp' and hasattr(user, 'app_command'):
            winege_exe_entry.set_text(user.app_command)

        # Função para limpar e normalizar o caminho quando o usuário digitar
        def on_exe_path_changed(entry):
            """Normalize path when user types it manually"""
            import urllib.parse
            text = entry.get_text().strip()
            if text and not text.endswith('.exe'):
                return  # Ainda está digitando

            if text:
                # Decodificar %20 e outros caracteres codificados
                text = urllib.parse.unquote(text)
                # Remover file:// se presente
                text = text.replace('file://', '')
                # Garantir que começa com /
                if text and not text.startswith('/'):
                    text = '/' + text
                # Atualizar o campo se mudou
                if text != entry.get_text():
                    entry.set_text(text)

        # Conectar eventos: quando pressionar Enter ou perder o foco
        winege_exe_entry.connect('apply', lambda e: on_exe_path_changed(winege_exe_entry))

        # GTK4 usa controller para eventos de foco
        focus_controller = Gtk.EventControllerFocus.new()
        focus_controller.connect('leave', lambda c: on_exe_path_changed(winege_exe_entry))
        winege_exe_entry.add_controller(focus_controller)

        winege_group.add(winege_exe_entry)
        settings_box.append(winege_group)

        # Função para toggle visibility based on session type
        def on_session_type_changed(combo, param=None):
            selected = combo.get_selected()
            is_desktop = selected == 0
            is_remoteapp = selected == 1
            is_winege = selected == 2

            # RemoteApp Linux
            remoteapp_group.set_visible(is_remoteapp)

            # WineGE RemoteApp
            winege_group.set_visible(is_winege)

        session_type_combo.connect('notify::selected', on_session_type_changed)

        # Initialize visibility
        on_session_type_changed(session_type_combo)

        # === Grupo: Segurança (Senha) ===
        security_group = Adw.PreferencesGroup()
        security_group.set_title("Security")
        security_group.set_description("Change the RDP password (leave blank to keep the current password)")

        password_entry = Adw.PasswordEntryRow()
        password_entry.set_title("New Password")
        security_group.add(password_entry)

        # Confirmação de senha
        confirm_entry = Adw.PasswordEntryRow()
        confirm_entry.set_title("Confirm Password")
        security_group.add(confirm_entry)

        settings_box.append(security_group)

        # Montar hierarquia: settings_box -> clamp -> scrolled -> toolbar_view -> dialog
        clamp.set_child(settings_box)
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)
        dialog.set_child(toolbar_view)

        # Conectar botão de salvar
        def on_save_clicked(button):
            """Handle save button click"""
            new_username = username_entry.get_text().strip()
            new_fullname = fullname_entry.get_text().strip()

            # Map index back to session type (AdwComboRow returns index)
            session_index = session_type_combo.get_selected()
            session_type_reverse_map = {0: 'desktop', 1: 'remoteapp', 2: 'winege-remoteapp'}
            new_session_type = session_type_reverse_map.get(session_index, 'desktop')

            new_password = password_entry.get_text()
            confirm_password = confirm_entry.get_text()
            original_username = user.username
            original_session_type = getattr(user, 'session_type', 'desktop')

            # Get RemoteApp data
            new_app_command = ''
            new_app_args = ''
            if new_session_type == 'remoteapp':
                # Pegar comando direto do campo de entrada
                new_app_command = custom_app_entry.get_text().strip()
                new_app_args = app_args_entry.get_text().strip()

                # Validar que app command não está vazio
                if not new_app_command:
                    self.show_toast("X Application command cannot be empty for RemoteApp")
                    return

            elif new_session_type == 'winege-remoteapp':
                # Pegar caminho do .exe
                new_app_command = winege_exe_entry.get_text().strip()
                new_app_args = ''  # WineGE não usa argumentos separados

                # Validar que .exe não está vazio e existe
                if not new_app_command:
                    self.show_toast("X Executable path cannot be empty for WineGE RemoteApp")
                    return

                from pathlib import Path
                if not Path(new_app_command).exists():
                    self.show_toast(f"X File not found: {new_app_command}")
                    return

            # Validar dados
            if not new_username:
                self.show_toast("X Username cannot be empty")
                return

            # Validar senha se fornecida
            if new_password or confirm_password:
                if new_password != confirm_password:
                    self.show_toast("X Passwords do not match")
                    return
                if len(new_password) < 6:
                    self.show_toast("X Password must be at least 6 characters long")
                    return

            # Call the existing save handler
            self._apply_user_changes(dialog, user, new_username, new_fullname, new_session_type,
                                     new_password, new_app_command, new_app_args, original_username,
                                     original_session_type)
            dialog.close()

        save_button.connect('clicked', on_save_clicked)

        dialog.present(self)

    def _apply_user_changes(self, dialog, user, new_username, new_fullname, new_session_type,
                           new_password, new_app_command, new_app_args, original_username,
                           original_session_type):
        """Apply user setting changes"""
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
                        changes_made.append("full name")
                    else:
                        GLib.idle_add(self.show_toast, "X Error changing full name")
                        return

                # 2. Alterar senha (se fornecida)
                if new_password:
                    success = self.user_manager.change_password(original_username, new_password)
                    if success:
                        changes_made.append("password")
                    else:
                        GLib.idle_add(self.show_toast, "X Error changing password")
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
                        changes_made.append("session type")
                    else:
                        GLib.idle_add(self.show_toast, "X Error changing session type")
                        return
                elif new_session_type == 'remoteapp':
                    # Mesmo tipo, mas pode ter mudado app/args
                    original_app = getattr(user, 'app_command', '')
                    original_args = getattr(user, 'app_args', '')

                    if new_app_command != original_app or new_app_args != original_args:
                        success = self.user_manager.change_user_session_type(
                            original_username, 'remoteapp', new_app_command, new_app_args
                        )
                        if success:
                            changes_made.append("RemoteApp application")
                        else:
                            GLib.idle_add(self.show_toast, "X Error changing application")
                            return

                elif new_session_type == 'winege-remoteapp':
                    # Mesmo tipo WineGE, mas pode ter mudado exe/args
                    original_app = getattr(user, 'app_command', '')
                    original_args = getattr(user, 'app_args', '')

                    if new_app_command != original_app or new_app_args != original_args:
                        # Atualizar executável se mudou
                        if new_app_command != original_app:
                            success = self.user_manager.update_winege_executable(
                                original_username, new_app_command
                            )
                            if not success:
                                GLib.idle_add(self.show_toast, "X Error updating WineGE executable")
                                return
                            changes_made.append("WineGE executable")

                        # Atualizar argumentos se mudou
                        if new_app_args != original_args:
                            success = self.user_manager.change_user_session_type(
                                original_username, 'winege-remoteapp', new_app_command, new_app_args
                            )
                            if success:
                                changes_made.append("WineGE arguments")
                            else:
                                GLib.idle_add(self.show_toast, "X Error changing arguments")
                                return

                # 4. Renomear usuário (último, pois muda o username)
                if new_username != original_username:
                    success = self.user_manager.rename_user(original_username, new_username)
                    if success:
                        changes_made.append("username")
                    else:
                        GLib.idle_add(self.show_toast, "X Error renaming user")
                        return

                # Mostrar sucesso
                if changes_made:
                    changes_text = ", ".join(changes_made)
                    GLib.idle_add(self.show_toast, f"OK Changed: {changes_text}")
                    GLib.timeout_add(300, self.load_users)
                else:
                    GLib.idle_add(self.show_toast, "ℹ No changes were made")

            except Exception as e:
                logger.error(f"Error updating user settings: {e}")
                GLib.idle_add(self.show_toast, "X Error updating settings")

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

        self.show_toast(f"OK {connection_string} copied!")

        # Fechar o popover
        popover.popdown()

    def show_password_dialog(self, user):
        """Show password dialog before connecting"""
        # Create dialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Connect to {user.username}",
            body="Enter the credentials to connect through RDP."
        )

        # Create credentials entry container
        creds_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        creds_box.set_margin_top(12)
        creds_box.set_margin_bottom(12)
        creds_box.set_margin_start(12)
        creds_box.set_margin_end(12)

        # Domain field (opcional)
        domain_label = Gtk.Label(label="Domain (optional):")
        domain_label.set_halign(Gtk.Align.START)
        creds_box.append(domain_label)

        domain_entry = Gtk.Entry()
        domain_entry.set_hexpand(True)
        domain_entry.set_can_focus(True)
        creds_box.append(domain_entry)

        # Password field
        password_label = Gtk.Label(label="Password:")
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
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("connect", "Connect")
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
                self.show_toast("X Password cannot be empty")
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
                self.show_toast("X FreeRDP not found")
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
                raise Exception(f"FreeRDP exited with code {process.returncode}: {error_msg[:200]}")

            # Mostrar mensagem de sucesso
            is_remoteapp = hasattr(user, 'session_type') and user.session_type == 'remoteapp'
            if is_remoteapp:
                app_name = user.app_command.split('/')[-1]
                self.show_toast(f"Opening RemoteApp: {app_name}...")
                logger.info(f"Launched RemoteApp {app_name} for user {user.username}")
            else:
                domain_suffix = f" (domain: {domain})" if domain else ""
                self.show_toast(f"Opening {freerdp_cmd}{domain_suffix}...")
                logger.info(f"Launched {freerdp_cmd} for user {user.username}{domain_suffix}")
        except FileNotFoundError:
            self.show_toast("X FreeRDP not found")
            logger.error("FreeRDP command not found")
        except Exception as e:
            logger.error(f"Error launching FreeRDP: {e}")
            self.show_toast(f"X Error opening FreeRDP: {e}")

    def on_copy_ip(self, button):
        """Copy IP to clipboard"""
        ip = self.session_monitor.get_ip_address()

        clipboard = self.get_clipboard()
        clipboard.set(ip)

        self.show_toast(f"OK IP {ip} copied!")
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
