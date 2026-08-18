#!/usr/bin/env python3
"""
Preferences Dialog
Application and Server Configuration with Capacity & Resource Limits.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import replace
from pathlib import Path
from typing import Optional

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import psutil

from core.server_manager import ServerManager
from core.server_config import ServerSettings, RESOURCE_PROFILES
from core.user_manager import UserManager

logger = logging.getLogger(__name__)


class PreferencesDialog(Adw.PreferencesWindow):
    """Application and system preferences window"""

    def __init__(self, parent, app_config, **kwargs):
        super().__init__(**kwargs)

        self.app_config = app_config
        self.server_manager = ServerManager()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_search_enabled(True)
        self.set_default_size(640, 560)

        # ---------------------------------------------------------------------
        # 1. Page: General Settings
        # ---------------------------------------------------------------------
        general_page = Adw.PreferencesPage()
        general_page.set_title("General")
        general_page.set_icon_name("preferences-other-symbolic")

        rdp_group = Adw.PreferencesGroup()
        rdp_group.set_title("RDP Server Port")
        rdp_group.set_description("Default port configuration for RDP client connections")

        self.port_row = Adw.SpinRow()
        self.port_row.set_title("Default Port")
        self.port_row.set_subtitle("Port used by RDP users (default: 3389)")

        port_adjustment = Gtk.Adjustment()
        port_adjustment.set_lower(1)
        port_adjustment.set_upper(65535)
        port_adjustment.set_step_increment(1)
        port_adjustment.set_page_increment(10)
        port_adjustment.set_value(self.app_config.get_default_rdp_port())

        self.port_row.set_adjustment(port_adjustment)
        self.port_row.set_digits(0)
        self.port_row.connect('changed', self.on_port_changed)

        rdp_group.add(self.port_row)
        general_page.add(rdp_group)
        self.add(general_page)

        # ---------------------------------------------------------------------
        # 2. Page: Server & Capacity Settings
        # ---------------------------------------------------------------------
        capacity_page = Adw.PreferencesPage()
        capacity_page.set_title("Server & Capacity")
        capacity_page.set_icon_name("network-server-symbolic")

        # Load current server settings
        self.server_settings = self.server_manager.config.load()
        self.resource_profiles = self.server_manager.config.load_resource_profiles()

        # Group: Session Capacity
        capacity_group = Adw.PreferencesGroup()
        capacity_group.set_title("Session Allocation")
        capacity_group.set_description("Concurrent session limits and resource reservation")

        # Linux Slots SpinRow
        self.linux_slots_row = Adw.SpinRow()
        self.linux_slots_row.set_title("Linux Session Slots")
        self.linux_slots_row.set_subtitle("1,280 MB RAM per slot (linux-light)")
        linux_adj = Gtk.Adjustment(
            value=self.server_settings.linux_session_slots,
            lower=0,
            upper=100,
            step_increment=1,
            page_increment=5,
        )
        self.linux_slots_row.set_adjustment(linux_adj)
        self.linux_slots_row.set_digits(0)
        self.linux_slots_row.connect('changed', self._on_capacity_inputs_changed)
        capacity_group.add(self.linux_slots_row)

        # Windows Slots SpinRow
        self.windows_slots_row = Adw.SpinRow()
        self.windows_slots_row.set_title("Windows / Wine Session Slots")
        self.windows_slots_row.set_subtitle("2,560 MB RAM per slot (windows-standard)")
        win_adj = Gtk.Adjustment(
            value=self.server_settings.windows_session_slots,
            lower=0,
            upper=100,
            step_increment=1,
            page_increment=5,
        )
        self.windows_slots_row.set_adjustment(win_adj)
        self.windows_slots_row.set_digits(0)
        self.windows_slots_row.connect('changed', self._on_capacity_inputs_changed)
        capacity_group.add(self.windows_slots_row)

        # Max Sessions SpinRow
        self.max_sessions_row = Adw.SpinRow()
        self.max_sessions_row.set_title("Max Concurrent Sessions")
        self.max_sessions_row.set_subtitle("Global ceiling for active RDP sessions")
        max_adj = Gtk.Adjustment(
            value=self.server_settings.max_sessions,
            lower=1,
            upper=200,
            step_increment=1,
            page_increment=10,
        )
        self.max_sessions_row.set_adjustment(max_adj)
        self.max_sessions_row.set_digits(0)
        self.max_sessions_row.connect('changed', self._on_capacity_inputs_changed)
        capacity_group.add(self.max_sessions_row)

        # Host Reserve SpinRow
        self.reserve_row = Adw.SpinRow()
        self.reserve_row.set_title("Host Memory Reserve (%)")
        self.reserve_row.set_subtitle("RAM reserved for system OS operations")
        res_adj = Gtk.Adjustment(
            value=self.server_settings.memory_reserve_percent,
            lower=5,
            upper=50,
            step_increment=5,
            page_increment=10,
        )
        self.reserve_row.set_adjustment(res_adj)
        self.reserve_row.set_digits(0)
        self.reserve_row.connect('changed', self._on_capacity_inputs_changed)
        capacity_group.add(self.reserve_row)

        capacity_page.add(capacity_group)

        # Group: Memory Safety Budget
        gauge_group = Adw.PreferencesGroup()
        gauge_group.set_title("Memory Safety Budget")

        self.memory_gauge_row = Adw.ActionRow()
        self.memory_gauge_row.set_title("Allocated Memory")
        self.memory_gauge_row.set_subtitle("Calculating…")

        self.status_badge = Gtk.Label()
        self.status_badge.add_css_class("heading")
        self.status_badge.set_valign(Gtk.Align.CENTER)
        self.memory_gauge_row.add_suffix(self.status_badge)

        gauge_group.add(self.memory_gauge_row)
        capacity_page.add(gauge_group)

        # Group: Network Security
        network_group = Adw.PreferencesGroup()
        network_group.set_title("Network Access Restriction")
        network_group.set_description("Restrict RDP access to a specific private network or VPN")

        self.network_row = Adw.EntryRow()
        self.network_row.set_title("Allowed Network (CIDR)")
        self.network_row.set_text(self.server_settings.allowed_network or "")
        self.network_row.set_show_apply_button(False)
        network_group.add(self.network_row)
        capacity_page.add(network_group)

        # Group: Actions & Apply
        actions_group = Adw.PreferencesGroup()
        actions_group.set_title("Capacity Management")

        # Recommend Action Row
        recommend_row = Adw.ActionRow()
        recommend_row.set_title("Auto-Detect Safe Capacity")
        recommend_row.set_subtitle("Automatically compute safe slots based on host RAM")

        recommend_btn = Gtk.Button(label="Recommend")
        recommend_btn.set_valign(Gtk.Align.CENTER)
        recommend_btn.connect('clicked', self.on_recommend_clicked)
        recommend_row.add_suffix(recommend_btn)
        actions_group.add(recommend_row)

        # Apply Action Row
        apply_row = Adw.ActionRow()
        apply_row.set_title("Apply Server Profile")
        apply_row.set_subtitle("Save settings and update system resource limits")

        self.apply_btn = Gtk.Button(label="Apply Changes")
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.set_valign(Gtk.Align.CENTER)
        self.apply_btn.connect('clicked', self.on_apply_server_profile)
        apply_row.add_suffix(self.apply_btn)
        actions_group.add(apply_row)

        capacity_page.add(actions_group)
        self.add(capacity_page)

        # Initial gauge update
        self._update_memory_gauge()

    def on_port_changed(self, spin_row):
        """Callback when RDP default port is altered"""
        new_port = int(spin_row.get_value())
        success = self.app_config.set_default_rdp_port(new_port)
        if success:
            logger.info(f"Default port changed to: {new_port}")
        else:
            logger.error(f"Error changing port to: {new_port}")

    def _on_capacity_inputs_changed(self, *args):
        """Update memory calculation when session slots or reserve percent change"""
        self._update_memory_gauge()

    def _update_memory_gauge(self):
        """Calculate requested RAM vs safe host budget"""
        linux_slots = int(self.linux_slots_row.get_value())
        windows_slots = int(self.windows_slots_row.get_value())
        reserve_pct = int(self.reserve_row.get_value())

        total_system_mb = int(psutil.virtual_memory().total / (1024 * 1024))
        safe_budget_mb = int(total_system_mb * (100 - reserve_pct) / 100)

        linux_mem = self.resource_profiles.get("linux-light", {}).get("memory_max_mb", 1280)
        win_mem = self.resource_profiles.get("windows-standard", {}).get("memory_max_mb", 2560)

        requested_mb = (linux_slots * linux_mem) + (windows_slots * win_mem)

        pct_used = int((requested_mb / safe_budget_mb) * 100) if safe_budget_mb > 0 else 100

        self.memory_gauge_row.set_subtitle(
            f"{requested_mb:,} MB requested / {safe_budget_mb:,} MB safe budget ({pct_used}% used • Total Host: {total_system_mb:,} MB)"
        )

        # Ensure max_sessions is at least sum of slots
        total_slots = linux_slots + windows_slots
        if int(self.max_sessions_row.get_value()) < total_slots:
            self.max_sessions_row.set_value(total_slots)

        if requested_mb <= safe_budget_mb:
            self.status_badge.set_label("✓ Safe Budget")
            self.status_badge.remove_css_class("error")
            self.status_badge.add_css_class("success")
        else:
            self.status_badge.set_label("⚠ Exceeds RAM")
            self.status_badge.remove_css_class("success")
            self.status_badge.add_css_class("error")

    def on_recommend_clicked(self, button):
        """Auto-compute slots fitting safely within host memory budget"""
        reserve_pct = int(self.reserve_row.get_value())
        total_system_mb = int(psutil.virtual_memory().total / (1024 * 1024))
        safe_budget_mb = int(total_system_mb * (100 - reserve_pct) / 100)

        linux_mem = self.resource_profiles.get("linux-light", {}).get("memory_max_mb", 1280)
        win_mem = self.resource_profiles.get("windows-standard", {}).get("memory_max_mb", 2560)

        # Distribute: If user already has some windows slots, reserve 1-2 windows slots, rest linux
        current_win = int(self.windows_slots_row.get_value())
        if current_win > 0:
            win_slots = min(2, max(1, safe_budget_mb // (win_mem * 3)))
            rem_budget = safe_budget_mb - (win_slots * win_mem)
            linux_slots = max(1, rem_budget // linux_mem)
        else:
            win_slots = 0
            linux_slots = max(1, safe_budget_mb // linux_mem)

        self.linux_slots_row.set_value(linux_slots)
        self.windows_slots_row.set_value(win_slots)
        self.max_sessions_row.set_value(linux_slots + win_slots)
        self._update_memory_gauge()

    def on_apply_server_profile(self, button):
        """Apply server profile via ServerManager in background thread"""
        linux_slots = int(self.linux_slots_row.get_value())
        windows_slots = int(self.windows_slots_row.get_value())
        max_sessions = int(self.max_sessions_row.get_value())
        reserve_pct = int(self.reserve_row.get_value())
        allowed_network = self.network_row.get_text().strip()

        updated_settings = replace(
            self.server_settings,
            linux_session_slots=linux_slots,
            windows_session_slots=windows_slots,
            max_sessions=max_sessions,
            memory_reserve_percent=reserve_pct,
            allowed_network=allowed_network,
        )

        self.apply_btn.set_sensitive(False)
        self.apply_btn.set_label("Applying…")

        def worker():
            try:
                assignments = {}
                for user in UserManager(app_config=self.app_config).list_users():
                    assignments[user.username] = (
                        'windows-standard'
                        if any(p.profile_type == 'winege-remoteapp' for p in user.profiles)
                        else user.default_profile.resource_profile
                    )

                self.server_manager.apply(
                    dry_run=False,
                    resource_assignments=assignments,
                    settings=updated_settings,
                )
                self.server_settings = updated_settings
                GLib.idle_add(self._on_apply_finished, True, "Server profile applied successfully")
            except Exception as exc:
                logger.error(f"Error applying server profile: {exc}")
                GLib.idle_add(self._on_apply_finished, False, str(exc))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_apply_finished(self, success: bool, message: str):
        self.apply_btn.set_sensitive(True)
        self.apply_btn.set_label("Apply Changes")

        parent_window = self.get_transient_for()
        if parent_window and hasattr(parent_window, "show_toast"):
            parent_window.show_toast(message)
        if success:
            if parent_window and hasattr(parent_window, "refresh_health"):
                parent_window.refresh_health()
            self.close()
