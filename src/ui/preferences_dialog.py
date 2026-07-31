#!/usr/bin/env python3
"""
Preferences Dialog
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw
import logging

logger = logging.getLogger(__name__)


class PreferencesDialog(Adw.PreferencesWindow):
    """Dialog de configurações da aplicação"""

    def __init__(self, parent, app_config, **kwargs):
        super().__init__(**kwargs)

        self.app_config = app_config
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_search_enabled(False)

        # Criar página de configurações
        page = Adw.PreferencesPage()
        page.set_title("Preferences")
        page.set_icon_name("preferences-system-symbolic")

        # Grupo de configurações RDP
        rdp_group = Adw.PreferencesGroup()
        rdp_group.set_title("RDP Server")
        rdp_group.set_description("xrdp server settings")

        # Campo de porta padrão
        self.port_row = Adw.SpinRow()
        self.port_row.set_title("Default Port")
        self.port_row.set_subtitle("Port used by all RDP users")

        # Configurar adjustment (min, max, step)
        adjustment = Gtk.Adjustment()
        adjustment.set_lower(1)
        adjustment.set_upper(65535)
        adjustment.set_step_increment(1)
        adjustment.set_page_increment(10)
        adjustment.set_value(self.app_config.get_default_rdp_port())

        self.port_row.set_adjustment(adjustment)
        self.port_row.set_digits(0)  # Sem casas decimais

        # Conectar sinal de mudança
        self.port_row.connect('changed', self.on_port_changed)

        rdp_group.add(self.port_row)

        # Adicionar grupo à página
        page.add(rdp_group)

        # Adicionar página à janela
        self.add(page)

    def on_port_changed(self, spin_row):
        """Callback quando porta é alterada"""
        new_port = int(spin_row.get_value())

        # Salvar configuração
        success = self.app_config.set_default_rdp_port(new_port)

        if success:
            logger.info(f"Default port changed to: {new_port}")
        else:
            logger.error(f"Error changing port to: {new_port}")
