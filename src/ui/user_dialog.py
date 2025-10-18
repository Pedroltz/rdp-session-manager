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
    de_combo = Gtk.Template.Child()
    install_de_switch = Gtk.Template.Child()
    auto_start_switch = Gtk.Template.Child()
    create_button = Gtk.Template.Child()
    cancel_button = Gtk.Template.Child()

    def __init__(self, parent, user_manager, rdp_config, de_installer, **kwargs):
        super().__init__(**kwargs)

        self.user_manager = user_manager
        self.rdp_config = rdp_config
        self.de_installer = de_installer

        self.setup_signals()
        self.setup_de_combo()

    def setup_signals(self):
        """Setup signal handlers"""
        self.create_button.connect('clicked', self.on_create_user)
        self.cancel_button.connect('clicked', lambda b: self.close())

        # Enable/disable create button based on validation
        self.username_entry.connect('changed', lambda e: self.validate_form())
        self.password_entry.connect('changed', lambda e: self.validate_form())
        self.confirm_password_entry.connect('changed', lambda e: self.validate_form())

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
            installed_mark = " ✓" if de['installed'] else ""
            label = f"{de['name']} (~{de['size_mb']}MB){installed_mark}"
            string_list.append(label)

            # Map index to DE id
            self.de_map[idx] = de['id']

        # Set the model to the combo box
        self.de_combo.set_model(string_list)

        # Set default selection to first item (usually the lightest DE)
        self.de_combo.set_selected(0)

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
        logger.info("INÍCIO DA CRIAÇÃO DE USUÁRIO RDP")
        logger.info("=" * 60)

        if not self.validate_form():
            logger.warning("Formulário inválido - criação abortada")
            return

        # Get form data
        username = self.username_entry.get_text()
        fullname = self.fullname_entry.get_text()
        password = self.password_entry.get_text()

        # Get selected DE
        de_idx = self.de_combo.get_selected()
        de_id = self.de_map.get(de_idx, 'xfce')

        logger.info(f"Dados do formulário:")
        logger.info(f"  - Username: {username}")
        logger.info(f"  - Fullname: {fullname}")
        logger.info(f"  - DE Index: {de_idx}")
        logger.info(f"  - DE ID: {de_id}")
        logger.info(f"  - DE Map: {self.de_map}")

        auto_start = self.auto_start_switch.get_active()
        install_de = self.install_de_switch.get_active()

        logger.info(f"  - Auto-start: {auto_start}")
        logger.info(f"  - Instalar DE: {install_de}")

        # Check if DE needs installation
        de_installed = self.de_installer.is_de_installed(de_id)
        logger.info(f"  - DE '{de_id}' já instalado: {de_installed}")

        if install_de and not de_installed:
            logger.info(f"→ Desktop Environment '{de_id}' precisa ser instalado primeiro")
            self.install_de_and_create_user(de_id, username, password, fullname)
        else:
            if not de_installed:
                logger.warning(f"⚠ DE '{de_id}' não está instalado mas usuário optou por não instalar")
            logger.info(f"→ Criando usuário diretamente (DE instalação: {install_de})")
            self.create_user(username, password, fullname, de_id)

    def install_de_and_create_user(self, de_id, username, password, fullname):
        """Install DE and then create user"""
        logger.info(f"→ INICIANDO INSTALAÇÃO DE DESKTOP ENVIRONMENT: {de_id}")

        # Get DE info
        de_info = self.de_installer.get_de_info(de_id)
        de_name = de_info['name'] if de_info else de_id.upper()

        logger.info(f"  - Nome: {de_name}")
        if de_info:
            logger.info(f"  - Tamanho: ~{de_info['size_mb']}MB")
            logger.info(f"  - Pacotes: {', '.join(de_info['packages'])}")

        # Show progress dialog with terminal log
        progress_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=f"Instalando {de_name}",
            body=f"Instalando Desktop Environment...\nIsso pode levar vários minutos."
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

        status_label = Gtk.Label(label="Preparando instalação...")
        status_label.add_css_class('title-3')
        header_box.append(status_label)

        main_box.append(header_box)

        # Expander para mostrar/ocultar terminal
        expander = Gtk.Expander()
        expander.set_label("📜 Ver Log de Instalação")
        expander.set_expanded(True)  # Expandido por padrão

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
                logger.info(f"✓ Instalação de {de_name} concluída com SUCESSO")
                append_log("✓ Instalação concluída com sucesso!")
                update_status("✓ Instalação concluída!")

                # Wait and then create user
                logger.info("→ Aguardando 1.5s antes de criar usuário...")
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.create_user(username, password, fullname, de_id))
            else:
                logger.error(f"✗ ERRO na instalação de {de_name}: {message}")
                append_log(f"✗ ERRO: {message}")
                update_status("✗ Erro na instalação")

                # Wait and show error dialog
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_de_install_error(message, username, password, fullname, de_id))

        def install_in_thread():
            try:
                GLib.idle_add(append_log, f"=== Instalando {de_name} ===")
                GLib.idle_add(append_log, f"DE ID: {de_id}")

                if de_info:
                    GLib.idle_add(append_log, f"Tamanho estimado: ~{de_info['size_mb']}MB")
                    GLib.idle_add(append_log, f"Pacotes: {', '.join(de_info['packages'][:3])}...")

                GLib.idle_add(append_log, "")
                GLib.idle_add(update_status, "Verificando espaço em disco...")

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
            update_status("Atualizando cache de pacotes...")
        elif progress == 30:
            update_status("Baixando e instalando pacotes...")
        elif progress == 100:
            update_status("Finalizando instalação...")

    def show_de_install_error(self, message, username, password, fullname, de_id):
        """Show DE installation error dialog"""
        error_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Erro na Instalação",
            body=f"{message}\n\nVocê pode continuar sem instalar o Desktop Environment se ele já estiver disponível."
        )
        error_dialog.add_response("cancel", "Cancelar")
        error_dialog.add_response("continue", "Continuar Mesmo Assim")
        error_dialog.set_response_appearance("continue", Adw.ResponseAppearance.SUGGESTED)
        error_dialog.connect("response", lambda d, r: self.handle_install_error(r, username, password, fullname, de_id))
        error_dialog.present()

    def handle_install_error(self, response, username, password, fullname, de_id):
        """Handle installation error response"""
        if response == "continue":
            self.create_user(username, password, fullname, de_id)

    def create_user(self, username, password, fullname, de_id):
        """Create the user"""
        logger.info("=" * 60)
        logger.info(f"→ INICIANDO CRIAÇÃO DO USUÁRIO: {username}")
        logger.info(f"  - Desktop Environment: {de_id}")
        logger.info("=" * 60)

        # Show progress with terminal log
        progress_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Criando Usuário RDP",
            body=f"Criando usuário {username}..."
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
                logger.info(f"✓ USUÁRIO {username} CRIADO COM SUCESSO!")
                logger.info(f"  - UID: {user.uid}")
                logger.info(f"  - Porta RDP: {user.rdp_port}")
                logger.info(f"  - Home: {user.home_dir}")
                logger.info(f"  - DE: {user.desktop_env}")
                append_log("✓ Usuário criado com sucesso!")

                # Wait a bit before closing
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_success_dialog(username, fullname, de_id, user))
            else:
                error = user_or_error
                logger.error(f"✗ ERRO AO CRIAR USUÁRIO {username}: {error}")
                append_log(f"✗ ERRO: {error}")

                # Wait before showing error dialog
                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_error_dialog(error))

        def create_in_thread():
            try:
                GLib.idle_add(append_log, "=== Criando Usuário RDP ===")
                GLib.idle_add(append_log, f"Usuário: {username}")
                GLib.idle_add(append_log, f"Desktop Environment: {de_id.upper()}")
                GLib.idle_add(append_log, "")

                # Create user with log callback
                GLib.idle_add(append_log, "→ Verificando grupo rdp-users...")
                user = self.user_manager.create_user(
                    username=username,
                    password=password,
                    desktop_env=de_id,
                    full_name=fullname,
                    log_callback=lambda msg: GLib.idle_add(append_log, msg)
                )

                if user:
                    GLib.idle_add(append_log, "")
                    GLib.idle_add(append_log, "→ Configurando sessão RDP...")

                    # Configure RDP session
                    self.rdp_config.create_user_session(
                        username=username,
                        uid=user.uid,
                        desktop_env=de_id,
                        rdp_port=user.rdp_port
                    )

                    GLib.idle_add(append_log, f"  Porta RDP: {user.rdp_port}")
                    GLib.idle_add(append_log, f"  UID: {user.uid}")
                    GLib.idle_add(append_log, "  Configuração concluída!")

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
        success_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="✓ Usuário Criado com Sucesso!",
            body=f"""Usuário: {username}
Nome: {fullname or username}
Desktop: {de_id.upper()}
Porta RDP: {user.rdp_port}

📡 Como Conectar:

Endereço: {self.get_connection_info(user.rdp_port)}

Linux:
  xfreerdp /v:{self.get_connection_info(user.rdp_port)} /u:{username}

Windows:
  Use "Conexão de Área de Trabalho Remota"
  Digite: {self.get_connection_info(user.rdp_port)}

✓ O usuário já aparece na lista principal!"""
        )

        success_dialog.add_response("ok", "Fechar")
        success_dialog.connect("response", lambda d, r: self.close())
        success_dialog.present()

        # Emit signal
        self.emit('user-created')
        logger.info(f"User {username} created successfully")

    def show_error_dialog(self, error):
        """Show error dialog"""
        error_dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Erro ao Criar Usuário",
            body=f"Não foi possível criar o usuário.\n\nErro: {error}\n\nVerifique:\n• Você tem permissões de administrador\n• O nome de usuário não existe\n• O grupo rdp-users foi criado"
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
