#!/usr/bin/env python3
"""
Tests for AppConfig module
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import AppConfig


class TestAppConfig(unittest.TestCase):
    """Test AppConfig class"""

    def setUp(self):
        """Setup test fixtures"""
        # Criar diretório temporário para testes
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / '.config' / 'rdp-session-manager'
        self.config_file = self.config_dir / 'config.ini'

    def tearDown(self):
        """Cleanup test fixtures"""
        # Remover diretório temporário
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('pathlib.Path.home')
    def test_config_initialization(self, mock_home):
        """Test AppConfig initialization"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        self.assertIsNotNone(config)
        self.assertTrue(config.config_dir.exists())
        self.assertTrue(config.config_file.exists())

    @patch('pathlib.Path.home')
    def test_config_default_values(self, mock_home):
        """Test AppConfig default values"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Verificar porta padrão
        default_port = config.get_default_rdp_port()
        self.assertEqual(default_port, 3389)

    @patch('pathlib.Path.home')
    def test_config_file_creation(self, mock_home):
        """Test that config file is created with defaults"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Arquivo deve existir
        self.assertTrue(config.config_file.exists())

        # Verificar conteúdo
        content = config.config_file.read_text()
        self.assertIn('[rdp]', content)
        self.assertIn('default_port', content)

    @patch('pathlib.Path.home')
    def test_get_default_rdp_port(self, mock_home):
        """Test get_default_rdp_port method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        port = config.get_default_rdp_port()

        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 1)
        self.assertLessEqual(port, 65535)

    @patch('pathlib.Path.home')
    def test_set_default_rdp_port(self, mock_home):
        """Test set_default_rdp_port method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Definir nova porta
        result = config.set_default_rdp_port(8080)
        self.assertTrue(result)

        # Verificar se foi salvo
        port = config.get_default_rdp_port()
        self.assertEqual(port, 8080)

    @patch('pathlib.Path.home')
    def test_set_default_rdp_port_invalid(self, mock_home):
        """Test set_default_rdp_port with invalid port"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Porta inválida (muito baixa)
        result = config.set_default_rdp_port(0)
        self.assertFalse(result)

        # Porta inválida (muito alta)
        result = config.set_default_rdp_port(70000)
        self.assertFalse(result)

        # Porta inválida (negativa)
        result = config.set_default_rdp_port(-1)
        self.assertFalse(result)

    @patch('pathlib.Path.home')
    def test_get_default_rdp_port_invalid_fallback(self, mock_home):
        """Test get_default_rdp_port fallback for invalid stored port"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Definir porta inválida manualmente no arquivo
        config.config.set('rdp', 'default_port', '999999')
        config._save()

        # Deve retornar 3389 como fallback
        port = config.get_default_rdp_port()
        self.assertEqual(port, 3389)

    @patch('pathlib.Path.home')
    def test_get_generic_value(self, mock_home):
        """Test generic get method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Obter valor padrão
        value = config.get('rdp', 'default_port')
        self.assertEqual(value, '3389')

        # Obter valor inexistente com fallback
        value = config.get('nonexistent', 'key', fallback='default_value')
        self.assertEqual(value, 'default_value')

    @patch('pathlib.Path.home')
    def test_set_generic_value(self, mock_home):
        """Test generic set method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Definir novo valor
        result = config.set('custom', 'setting', 'test_value')
        self.assertTrue(result)

        # Verificar se foi salvo
        value = config.get('custom', 'setting')
        self.assertEqual(value, 'test_value')

    @patch('pathlib.Path.home')
    def test_set_creates_section(self, mock_home):
        """Test that set creates section if it doesn't exist"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Definir valor em seção inexistente
        result = config.set('newsection', 'key', 'value')
        self.assertTrue(result)

        # Verificar que seção foi criada
        self.assertTrue(config.config.has_section('newsection'))

        # Verificar valor
        value = config.get('newsection', 'key')
        self.assertEqual(value, 'value')

    @patch('pathlib.Path.home')
    def test_config_persistence(self, mock_home):
        """Test that config persists across instances"""
        mock_home.return_value = self.test_dir

        # Primeira instância
        config1 = AppConfig()
        config1.set_default_rdp_port(5000)

        # Segunda instância (deve carregar do arquivo)
        config2 = AppConfig()
        port = config2.get_default_rdp_port()

        self.assertEqual(port, 5000)

    @patch('pathlib.Path.home')
    def test_config_load_existing(self, mock_home):
        """Test loading existing config file"""
        mock_home.return_value = self.test_dir

        # Criar primeira instância
        config1 = AppConfig()
        config1.set('test', 'key', 'value')

        # Criar segunda instância (deve carregar arquivo existente)
        config2 = AppConfig()
        value = config2.get('test', 'key')

        self.assertEqual(value, 'value')

    @patch('pathlib.Path.home')
    def test_config_ensures_defaults(self, mock_home):
        """Test that missing default sections/keys are added"""
        mock_home.return_value = self.test_dir

        # Criar config sem alguns defaults
        config_dir = self.test_dir / '.config' / 'rdp-session-manager'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.ini'

        # Criar arquivo incompleto
        config_file.write_text('[other]\nkey=value\n')

        # Carregar config (deve adicionar defaults)
        config = AppConfig()

        # Verificar que defaults foram adicionados
        self.assertTrue(config.config.has_section('rdp'))
        self.assertTrue(config.config.has_option('rdp', 'default_port'))

    @patch('pathlib.Path.home')
    def test_config_invalid_file_recreates(self, mock_home):
        """Test that invalid config file is recreated"""
        mock_home.return_value = self.test_dir

        config_dir = self.test_dir / '.config' / 'rdp-session-manager'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.ini'

        # Criar arquivo inválido
        config_file.write_text('invalid config content [[[')

        # Carregar config (deve recriar com defaults)
        config = AppConfig()

        # Deve ter valores padrão
        port = config.get_default_rdp_port()
        self.assertEqual(port, 3389)

    @patch('pathlib.Path.home')
    def test_config_multiple_sections(self, mock_home):
        """Test config with multiple sections"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Adicionar valores em múltiplas seções
        config.set('section1', 'key1', 'value1')
        config.set('section2', 'key2', 'value2')
        config.set('section3', 'key3', 'value3')

        # Verificar todos os valores
        self.assertEqual(config.get('section1', 'key1'), 'value1')
        self.assertEqual(config.get('section2', 'key2'), 'value2')
        self.assertEqual(config.get('section3', 'key3'), 'value3')

    @patch('pathlib.Path.home')
    def test_config_overwrite_value(self, mock_home):
        """Test overwriting existing config value"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Definir valor inicial
        config.set('test', 'key', 'value1')
        self.assertEqual(config.get('test', 'key'), 'value1')

        # Sobrescrever
        config.set('test', 'key', 'value2')
        self.assertEqual(config.get('test', 'key'), 'value2')


if __name__ == '__main__':
    unittest.main()
