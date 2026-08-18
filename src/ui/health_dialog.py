#!/usr/bin/env python3
"""Detailed GTK health report with filtering and evidence inspection."""

import logging
import threading

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk


logger = logging.getLogger(__name__)


class HealthDialog(Adw.Dialog):
    STATUS_VALUES = ("", "healthy", "warning", "critical", "unknown")
    SCOPE_VALUES = ("", "host", "user", "session", "windows-runtime")

    def __init__(self, health_service, initial_report=None, on_report=None, **kwargs):
        super().__init__(**kwargs)
        self.health_service = health_service
        self.report = initial_report
        self.on_report = on_report
        self._refreshing = False

        self.set_title("System Health")
        self.set_content_width(720)
        self.set_content_height(560)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="System Health"))
        self.refresh_button = Gtk.Button(icon_name="view-refresh-symbolic")
        self.refresh_button.set_tooltip_text("Check system health now")
        self.refresh_button.connect("clicked", self.refresh)
        header.pack_end(self.refresh_button)
        toolbar.add_top_bar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)

        self.summary = Gtk.Label()
        self.summary.set_halign(Gtk.Align.START)
        self.summary.add_css_class("title-3")
        root.append(self.summary)

        filters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status_filter = self._dropdown(
            ("All statuses", "Healthy", "Warning", "Critical", "Unknown")
        )
        self.status_filter.set_tooltip_text("Filter by severity")
        self.scope_filter = self._dropdown(
            ("All components", "Host", "User", "Session", "Windows runtime")
        )
        self.scope_filter.set_tooltip_text("Filter by component")
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search user, check, or evidence…")
        self.search.set_hexpand(True)
        filters.append(self.status_filter)
        filters.append(self.scope_filter)
        filters.append(self.search)
        root.append(filters)

        self.status_filter.connect("notify::selected", self._filters_changed)
        self.scope_filter.connect("notify::selected", self._filters_changed)
        self.search.connect("search-changed", self._filters_changed)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        scrolled.set_child(self.listbox)
        root.append(scrolled)

        self.empty = Gtk.Label(label="No checks match the selected filters.")
        self.empty.add_css_class("dim-label")
        self.empty.set_visible(False)
        root.append(self.empty)

        toolbar.set_content(root)
        self.set_child(toolbar)

        if self.report is None:
            GLib.idle_add(self.refresh)
        else:
            self.render()

    @staticmethod
    def _dropdown(labels):
        model = Gtk.StringList()
        for label in labels:
            model.append(label)
        dropdown = Gtk.DropDown(model=model)
        dropdown.set_selected(0)
        return dropdown

    def refresh(self, button=None):
        if self._refreshing:
            return False
        self._refreshing = True
        self.refresh_button.set_sensitive(False)
        self.summary.set_text("Checking host, users and sessions…")

        def worker():
            try:
                report = self.health_service.collect()
                GLib.idle_add(self._refresh_finished, report, None)
            except Exception as exc:
                logger.error("Detailed health refresh failed: %s", exc)
                GLib.idle_add(self._refresh_finished, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()
        return False

    def _refresh_finished(self, report, error):
        self._refreshing = False
        self.refresh_button.set_sensitive(True)
        if error or report is None:
            self.summary.set_text("Health check unavailable")
            return False
        self.report = report
        self.render()
        if self.on_report:
            self.on_report(report)
        return False

    def _filters_changed(self, widget, param=None):
        self.render()

    def render(self):
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        if self.report is None:
            self.summary.set_text("No health report is available.")
            self.empty.set_visible(True)
            return

        counts = self.report.counts
        self.summary.set_text(
            f"{self.report.overall_status.upper()} · "
            f"{counts['critical']} critical · {counts['warning']} warning · "
            f"{counts['healthy']} healthy"
        )
        status = self.STATUS_VALUES[self.status_filter.get_selected()]
        scope = self.SCOPE_VALUES[self.scope_filter.get_selected()]
        checks = self.report.filter_checks(status, scope, self.search.get_text())
        for check in checks:
            self.listbox.append(self._check_row(check))
        self.empty.set_visible(not checks)

    def _check_row(self, check):
        row = Adw.ExpanderRow()
        row.set_title(check.summary)
        row.set_subtitle(f"{check.scope} · {check.target} · {check.status}")
        icon_names = {
            "healthy": "emblem-ok-symbolic",
            "warning": "dialog-warning-symbolic",
            "critical": "dialog-error-symbolic",
            "unknown": "dialog-question-symbolic",
        }
        icon = Gtk.Image.new_from_icon_name(icon_names[check.status])
        row.add_prefix(icon)

        identifier = Adw.ActionRow(title="Check ID", subtitle=check.check_id)
        row.add_row(identifier)
        for key, value in sorted(check.evidence.items()):
            rendered = self._render_evidence(value)
            evidence = Adw.ActionRow(
                title=key.replace("_", " ").title(),
                subtitle=rendered,
            )
            evidence.set_subtitle_lines(8)
            row.add_row(evidence)
        if check.remediation_id:
            remediation = Adw.ActionRow(
                title="Available remediation",
                subtitle=check.remediation_id,
            )
            row.add_row(remediation)
        return row

    @classmethod
    def _render_evidence(cls, value):
        """Render structured evidence for people instead of exposing raw JSON."""
        if isinstance(value, list):
            return "\n".join(f"• {cls._render_evidence(item)}" for item in value) or "None"
        if isinstance(value, dict):
            return "\n".join(
                f"{key.replace('_', ' ').title()}: {cls._render_evidence(item)}"
                for key, item in value.items()
            ) or "None"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if value is None or value == "":
            return "None"
        return str(value)
