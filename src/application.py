#!/usr/bin/env python3
"""
RDP Session Manager - Main Application
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
import logging
import threading

from ui.main_window import MainWindow
from ui.preferences_dialog import PreferencesDialog
from core.user_manager import UserManager
from core.rdp_config import RDPConfig
from core.de_installer import DEInstaller
from core.session_monitor import SessionMonitor
from core.system_deps import SystemDependencies
from core.config import AppConfig

logger = logging.getLogger(__name__)


class RDPSessionManagerApp(Adw.Application):
    """Main application class"""

    def __init__(self):
        super().__init__(
            application_id='com.rdp.SessionManager',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        self.window = None

        # Core components
        self.user_manager = None
        self.rdp_config = None
        self.de_installer = None
        self.session_monitor = None
        self.system_deps = None
        self.app_config = None

    def do_startup(self):
        """Called on application startup"""
        Adw.Application.do_startup(self)

        # Initialize configuration first
        self.app_config = AppConfig()

        # Initialize core components
        self.user_manager = UserManager(self.app_config)
        self.rdp_config = RDPConfig()
        self.de_installer = DEInstaller()
        self.session_monitor = SessionMonitor()
        self.system_deps = SystemDependencies()

        # Setup actions
        self.create_actions()

        # Load CSS
        self.load_css()

        logger.info("Application startup complete")

    def do_activate(self):
        """Called when application is activated"""
        if not self.window:
            self.window = MainWindow(
                application=self,
                user_manager=self.user_manager,
                rdp_config=self.rdp_config,
                de_installer=self.de_installer,
                session_monitor=self.session_monitor,
                system_deps=self.system_deps
            )

        self.window.present()

        # Check system dependencies (xrdp)
        GLib.idle_add(self.check_system_dependencies)

    def create_actions(self):
        """Create application actions"""
        # Preferences action
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self.on_preferences)
        self.add_action(preferences_action)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

        # Keyboard shortcuts
        self.set_accels_for_action("app.quit", ["<Ctrl>Q"])
        self.set_accels_for_action("app.preferences", ["<Ctrl>comma"])

    def on_preferences(self, action, param):
        """Show preferences dialog"""
        preferences = PreferencesDialog(self.window, self.app_config)
        preferences.present()

    def on_about(self, action, param):
        """Show about dialog"""
        from pathlib import Path
        from gi.repository import Gdk

        about = Adw.AboutDialog(
            application_name="RDP Session Manager",
            application_icon="com.rdp.SessionManager",
            developer_name="Pedroltz",
            version="0.3.0",
            developers=["Pedroltz"],
            copyright="© 2025 Pedroltz",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/Pedroltz/rdp-session-manager",
            issue_url="https://github.com/Pedroltz/rdp-session-manager/issues"
        )

        # Try to load custom logo image
        logo_path = Path(__file__).parent.parent / "imgs" / "RDPSM.png"
        if logo_path.exists():
            try:
                texture = Gdk.Texture.new_from_filename(str(logo_path))
                about.set_application_icon("com.rdp.SessionManager")
            except Exception as e:
                logger.warning(f"Could not load logo image: {e}")

        about.present(self.window)

    def check_system_dependencies(self):
        """Check and install system dependencies if needed"""
        all_ok, missing, installed = self.system_deps.check_dependencies()

        if not all_ok:
            logger.warning(f"Missing dependencies: {missing}")

            # Check if xrdp is missing
            if 'xrdp' in missing:
                self.show_xrdp_install_dialog()

        return False  # Don't repeat

    def show_xrdp_install_dialog(self):
        """Show dialog to install xrdp"""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Servidor xrdp não encontrado",
            body="O servidor xrdp é necessário para criar sessões RDP remotas.\n\nDeseja instalar agora?"
        )

        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("install", "Instalar xrdp")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self.on_xrdp_install_response)
        dialog.present()

    def on_xrdp_install_response(self, dialog, response):
        """Handle xrdp installation response"""
        if response == "install":
            self.install_xrdp_with_progress()

    def install_xrdp_with_progress(self):
        """Install xrdp with progress dialog"""
        # Create progress dialog
        progress_dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Instalando xrdp",
            body="Instalando servidor RDP...\nIsso pode levar alguns minutos."
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

        # CSS for terminal
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
        main_box.append(scrolled)

        progress_dialog.set_extra_child(main_box)
        progress_dialog.present()

        def append_log(message):
            """Append to log"""
            end_iter = text_buffer.get_end_iter()
            text_buffer.insert(end_iter, f"{message}\n", -1)
            mark = text_buffer.create_mark(None, text_buffer.get_end_iter(), False)
            text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        def update_status(text):
            """Update status label"""
            status_label.set_label(text)

        def on_install_complete(success, message):
            spinner.stop()

            if success:
                append_log("OK xrdp instalado e configurado com sucesso!")
                update_status("OK Instalação concluída!")

                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_xrdp_success())
            else:
                append_log(f"X ERRO: {message}")
                update_status("X Erro na instalação")

                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_xrdp_error(message))

        def install_in_thread():
            try:
                GLib.idle_add(append_log, "=== Instalando xrdp ===")
                GLib.idle_add(append_log, "")
                GLib.idle_add(update_status, "Instalando xrdp...")

                success, message = self.system_deps.install_package(
                    'xrdp',
                    progress_callback=lambda progress, msg: GLib.idle_add(append_log, msg)
                )

                GLib.idle_add(on_install_complete, success, message)

            except Exception as e:
                logger.error(f"Error installing xrdp: {e}")
                GLib.idle_add(on_install_complete, False, str(e))

        thread = threading.Thread(target=install_in_thread)
        thread.daemon = True
        thread.start()

    def show_xrdp_success(self):
        """Show xrdp installation success"""
        # Atualizar status na janela principal
        if self.window and hasattr(self.window, 'update_xrdp_status'):
            self.window.update_xrdp_status()

        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="OK xrdp Instalado!",
            body="O servidor xrdp foi instalado e configurado com sucesso.\n\nAgora você pode criar usuários RDP!"
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def show_xrdp_error(self, error):
        """Show xrdp installation error"""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Erro na Instalação do xrdp",
            body=f"Não foi possível instalar o xrdp.\n\nErro: {error}\n\nO servidor xrdp é NECESSÁRIO para criar usuários RDP.\n\nVocê pode:\n• Tentar instalar novamente\n• Instalar manualmente: sudo apt install xrdp"
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("retry", "Tentar Novamente")
        dialog.add_response("manual", "Ver Instruções")
        dialog.set_response_appearance("retry", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self.on_xrdp_error_response)
        dialog.present()

    def on_xrdp_error_response(self, dialog, response):
        """Handle xrdp error dialog response"""
        if response == "retry":
            # Tentar instalar novamente
            self.install_xrdp_with_progress()
        elif response == "manual":
            # Mostrar instruções de instalação manual
            self.show_manual_install_instructions()

    def show_manual_install_instructions(self):
        """Show manual installation instructions"""
        instructions = """Para instalar o xrdp manualmente, execute os seguintes comandos no terminal:

1. Atualizar lista de pacotes:
   sudo apt update

2. Instalar xrdp:
   sudo apt install -y xrdp xorgxrdp

3. Habilitar e iniciar o serviço:
   sudo systemctl enable xrdp
   sudo systemctl start xrdp

4. Verificar se está rodando:
   sudo systemctl status xrdp

Após a instalação manual, reinicie esta aplicação para que o xrdp seja detectado."""

        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Instalação Manual do xrdp",
            body=instructions
        )
        dialog.add_response("close", "Fechar")
        dialog.add_response("copy", "Copiar Comandos")
        dialog.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda d, r: self.on_manual_instructions_response(r, instructions))
        dialog.present()

    def on_manual_instructions_response(self, response, instructions):
        """Handle manual instructions response"""
        if response == "copy":
            # Copiar comandos para clipboard
            clipboard = self.window.get_clipboard()
            commands = """sudo apt update
sudo apt install -y xrdp xorgxrdp
sudo systemctl enable xrdp
sudo systemctl start xrdp
sudo systemctl status xrdp"""
            clipboard.set(commands)

            # Mostrar toast
            if hasattr(self.window, 'show_toast'):
                self.window.show_toast("OK Comandos copiados para a área de transferência!")

    def install_freerdp_with_progress(self):
        """Install FreeRDP with progress dialog"""
        # Create progress dialog
        progress_dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Instalando FreeRDP",
            body="Instalando cliente RDP...\nIsso pode levar alguns minutos."
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

        # CSS for terminal
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
        main_box.append(scrolled)

        progress_dialog.set_extra_child(main_box)
        progress_dialog.present()

        def append_log(message):
            """Append to log"""
            end_iter = text_buffer.get_end_iter()
            text_buffer.insert(end_iter, f"{message}\n", -1)
            mark = text_buffer.create_mark(None, text_buffer.get_end_iter(), False)
            text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        def update_status(text):
            """Update status label"""
            status_label.set_label(text)

        def on_install_complete(success, message):
            spinner.stop()

            if success:
                append_log("OK FreeRDP instalado com sucesso!")
                update_status("OK Instalação concluída!")

                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_freerdp_success())
            else:
                append_log(f"X ERRO: {message}")
                update_status("X Erro na instalação")

                GLib.timeout_add(1500, lambda: progress_dialog.close())
                GLib.timeout_add(1600, lambda: self.show_freerdp_error(message))

        def install_in_thread():
            try:
                GLib.idle_add(append_log, "=== Instalando FreeRDP ===")
                GLib.idle_add(append_log, "")
                GLib.idle_add(update_status, "Instalando FreeRDP...")

                success, message = self.system_deps.install_package(
                    'freerdp',
                    progress_callback=lambda progress, msg: GLib.idle_add(append_log, msg)
                )

                GLib.idle_add(on_install_complete, success, message)

            except Exception as e:
                logger.error(f"Error installing FreeRDP: {e}")
                GLib.idle_add(on_install_complete, False, str(e))

        thread = threading.Thread(target=install_in_thread)
        thread.daemon = True
        thread.start()

    def show_freerdp_success(self):
        """Show FreeRDP installation success"""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="OK FreeRDP Instalado!",
            body="O cliente FreeRDP foi instalado com sucesso.\n\nAgora você pode conectar aos seus usuários RDP!"
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def show_freerdp_error(self, error):
        """Show FreeRDP installation error"""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Erro na Instalação do FreeRDP",
            body=f"Não foi possível instalar o FreeRDP.\n\nErro: {error}\n\nVocê pode:\n• Tentar instalar novamente\n• Instalar manualmente: sudo apt install freerdp3-x11"
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("retry", "Tentar Novamente")
        dialog.set_response_appearance("retry", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self.on_freerdp_error_response)
        dialog.present()

    def on_freerdp_error_response(self, dialog, response):
        """Handle FreeRDP error dialog response"""
        if response == "retry":
            # Tentar instalar novamente
            self.install_freerdp_with_progress()

    def load_css(self):
        """Load custom CSS"""
        from gi.repository import Gdk

        css_provider = Gtk.CssProvider()

        # Custom CSS
        css = b"""
        .user-card {
            padding: 12px;
            border-radius: 8px;
        }

        .status-indicator {
            min-width: 12px;
            min-height: 12px;
            border-radius: 6px;
        }

        .status-active {
            background-color: @success_color;
        }

        .status-inactive {
            background-color: @window_bg_color;
            border: 1px solid @borders;
        }
        """

        css_provider.load_from_data(css)

        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
