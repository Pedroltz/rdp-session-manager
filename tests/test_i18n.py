#!/usr/bin/env python3
"""Tests for internationalization (i18n) module."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.i18n import (
    _,
    get_text,
    get_current_language,
    set_language,
    detect_system_language,
    register_language,
    get_available_languages,
)


class TestI18n(unittest.TestCase):
    def setUp(self):
        set_language("en")

    def test_default_english_fallback(self):
        set_language("en")
        self.assertEqual(_("Cancel"), "Cancel")
        self.assertEqual(_("Apply Changes"), "Apply Changes")

    def test_portuguese_translation(self):
        set_language("pt_BR")
        self.assertEqual(_("Cancel"), "Cancelar")
        self.assertEqual(_("Apply Changes"), "Aplicar Alterações")
        self.assertEqual(
            _("Please enter an allowed network in CIDR format (e.g., 192.168.1.0/24)"),
            "Preencha a rede permitida em formato CIDR (ex: 192.168.1.0/24)"
        )

    def test_spanish_translation(self):
        set_language("es")
        self.assertEqual(_("Cancel"), "Cancelar")
        self.assertEqual(_("Apply Changes"), "Aplicar Cambios")

    def test_untranslated_string_returns_original(self):
        set_language("pt_BR")
        original = "Some very custom string that is not translated"
        self.assertEqual(_(original), original)

    def test_formatting_placeholders(self):
        set_language("en")
        msg = _("Port: {port}", port=3389)
        self.assertEqual(msg, "Port: 3389")

    def test_register_new_language(self):
        register_language("fr", {
            "Cancel": "Annuler",
            "OK": "D'accord",
            "Apply Changes": "Appliquer les modifications",
        })
        set_language("fr")
        self.assertEqual(_("Cancel"), "Annuler")
        self.assertEqual(_("Apply Changes"), "Appliquer les modifications")
        self.assertIn("fr", get_available_languages())

    @patch.dict('os.environ', {'LANG': 'pt_BR.UTF-8', 'LC_ALL': '', 'LC_MESSAGES': ''}, clear=True)
    def test_detect_system_language_pt(self):
        detected = detect_system_language()
        self.assertEqual(detected, "pt_BR")

    @patch.dict('os.environ', {'LANG': 'es_ES.UTF-8', 'LC_ALL': '', 'LC_MESSAGES': ''}, clear=True)
    def test_detect_system_language_es(self):
        detected = detect_system_language()
        self.assertEqual(detected, "es")

    @patch.dict('os.environ', {'LANG': 'C', 'LC_ALL': '', 'LC_MESSAGES': ''}, clear=True)
    def test_detect_system_language_fallback_en(self):
        detected = detect_system_language()
        self.assertEqual(detected, "en")


if __name__ == '__main__':
    unittest.main()
