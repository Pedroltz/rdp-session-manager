# Documentação de Desenvolvimento

## Progresso do Projeto

### ✅ Fase 1: Estrutura Base (100% Completo)

- [x] Estrutura de diretórios criada
- [x] Sistema de build configurado (Meson + setuptools)
- [x] Metadados da aplicação (Desktop file, AppData, GSchema)
- [x] PolicyKit configurado para ações administrativas

### ✅ Fase 2: Backend Core (100% Completo)

- [x] Módulo de gerenciamento de usuários (`user_manager.py`)
  - Criação, exclusão, listagem de usuários RDP
  - Validação de nomes de usuário
  - Geração automática de UID e portas

- [x] Sistema de configuração FreeRDP (`rdp_config.py`)
  - Geração de configuração xrdp
  - Scripts de inicialização de sessão
  - Suporte para múltiplos DEs

- [x] Instalador automático de DEs (`de_installer.py`)
  - Suporte para GNOME, XFCE, KDE, MATE, Cinnamon, LXDE, LXQt
  - Verificação de espaço em disco
  - Detecção de DEs instalados

- [x] Monitoramento de sessões (`session_monitor.py`)
  - Detecção de sessões ativas
  - Monitoramento de recursos do sistema
  - Obtenção de IPs e portas

### ✅ Fase 3: Interface GTK4 (100% Completo)

- [x] Janela principal (`main-window.ui`)
  - Lista de usuários RDP
  - Informações do servidor
  - Busca de usuários

- [x] Diálogo de criação de usuário (`user-dialog.ui`)
  - Formulário completo
  - Validação em tempo real
  - Seleção de DE

- [x] Implementação Python da UI
  - `MainWindow` com atualização em tempo real
  - `UserDialog` com validação
  - Integração com backend

### ✅ Fase 4: Integração e Segurança (100% Completo)

- [x] PolicyKit Helper (`rdp-session-helper.py`)
  - Criação/exclusão de usuários
  - Instalação de pacotes
  - Gerenciamento de sessões

- [x] Sistema de validação (`validator.py`)
  - Validação de username, senha, porta
  - Sanitização de entrada

- [x] Sistema de logs (`logger.py`)
  - Logs rotativos
  - Auditoria JSON
  - Múltiplos níveis de log

- [x] Sistema de backup (`backup.py`)
  - Backup de configurações
  - Restauração
  - Limpeza automática

### ✅ Fase 5: Testes e Documentação (100% Completo)

- [x] Testes unitários
  - `test_validator.py`
  - `test_user_manager.py`

- [x] Documentação completa
  - README.md com instruções
  - Documentação de desenvolvimento
  - Guia de problemas conhecidos

## Arquitetura do Sistema

### Componentes Principais

```
┌─────────────────────────────────────────────┐
│          Interface GTK4 (UI)                │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │ MainWindow   │      │  UserDialog     │ │
│  └──────────────┘      └─────────────────┘ │
└─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────┐
│         Core Modules (Backend)              │
│  ┌──────────────┐  ┌──────────────────────┐│
│  │UserManager   │  │  RDPConfig           ││
│  └──────────────┘  └──────────────────────┘│
│  ┌──────────────┐  ┌──────────────────────┐│
│  │DEInstaller   │  │  SessionMonitor      ││
│  └──────────────┘  └──────────────────────┘│
└─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────┐
│      Utilities & Security                   │
│  ┌──────────────┐  ┌──────────────────────┐│
│  │PolicyKit     │  │  Validator           ││
│  │Helper        │  │                      ││
│  └──────────────┘  └──────────────────────┘│
│  ┌──────────────┐  ┌──────────────────────┐│
│  │Logger        │  │  Backup              ││
│  └──────────────┘  └──────────────────────┘│
└─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────┐
│         Sistema Operacional                 │
│    Linux Users, xrdp, Desktop Environments  │
└─────────────────────────────────────────────┘
```

### Fluxo de Criação de Usuário

1. **UI**: Usuário preenche formulário
2. **Validação**: Validator verifica dados
3. **UserManager**: Cria estrutura do usuário
4. **PolicyKit**: Solicita privilégios admin
5. **Helper**: Executa `useradd` com privilégios
6. **RDPConfig**: Configura sessão xrdp
7. **DEInstaller**: Instala DE se necessário
8. **Audit**: Registra ação nos logs
9. **Backup**: Cria backup da configuração
10. **UI**: Atualiza lista de usuários

## API Interna

### UserManager

```python
# Criar usuário
user = user_manager.create_user(
    username="joao",
    password="SenhaForte123",
    desktop_env="xfce",
    full_name="João Silva"
)

# Listar usuários
users = user_manager.list_users()

# Obter usuário específico
user = user_manager.get_user("joao")

# Excluir usuário
success = user_manager.delete_user("joao", remove_home=True)
```

### RDPConfig

```python
# Criar configuração de sessão
rdp_config.create_user_session(
    username="joao",
    uid=5000,
    desktop_env="xfce",
    rdp_port=3389
)

# Obter status da sessão
status = rdp_config.get_session_status("joao")

# Portas disponíveis
ports = rdp_config.get_available_ports(start_port=3389, count=10)
```

### SessionMonitor

```python
# Obter sessões ativas
sessions = session_monitor.get_active_sessions()

# Verificar se usuário está conectado
is_connected = session_monitor.is_user_connected("joao")

# Obter IP do servidor
ip = session_monitor.get_ip_address()

# Estatísticas do sistema
stats = session_monitor.get_system_stats()
```

## Desenvolvimento

### Setup do Ambiente

```bash
# Clone e entre no diretório
git clone <repo>
cd RemoteApps-RDP

# Crie virtual environment
python3 -m venv venv
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
pip install pytest

# Execute em modo desenvolvimento
python3 src/main.py
```

### Adicionar Novo Desktop Environment

1. Edite `src/core/de_installer.py`
2. Adicione entrada em `DE_PACKAGES`:

```python
'budgie': {
    'name': 'Budgie',
    'packages': ['budgie-desktop', 'budgie-extras'],
    'size_mb': 500,
    'startup_cmd': 'budgie-desktop'
}
```

3. Teste a instalação

### Adicionar Nova Validação

1. Edite `src/utils/validator.py`
2. Adicione método estático:

```python
@staticmethod
def validate_something(value: str) -> Tuple[bool, str]:
    if not value:
        return False, "Value cannot be empty"
    return True, ""
```

### Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Teste específico
pytest tests/test_validator.py -v

# Com cobertura
pytest tests/ --cov=src --cov-report=html
```

## Padrões de Código

### Python

- **PEP 8**: Seguir guia de estilo
- **Type Hints**: Usar quando possível
- **Docstrings**: Documentar todas as funções públicas
- **Logging**: Usar logger ao invés de print

### GTK/UI

- **Templates**: Usar Gtk.Template para UI
- **Signals**: Conectar via `connect()`
- **CSS Classes**: Usar classes do Adwaita quando possível

### Git

- **Commits**: Mensagens claras e descritivas
- **Branches**: `feature/`, `bugfix/`, `hotfix/`
- **Pull Requests**: Um feature por PR

## Depuração

### Habilitar Logs de Debug

```bash
# Variável de ambiente
export G_MESSAGES_DEBUG=all
export GTK_DEBUG=interactive

# Execute a aplicação
python3 src/main.py
```

### Logs do Sistema

```bash
# Logs da aplicação
tail -f ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log

# Logs de auditoria
tail -f ~/.local/share/rdp-session-manager/logs/audit.log

# Logs do xrdp
sudo tail -f /var/log/xrdp/xrdp.log
```

### Debug do PolicyKit

```bash
# Verificar política instalada
pkaction --verbose --action-id com.rdp.SessionManager.create-user

# Testar autorização
pkcheck --action-id com.rdp.SessionManager.create-user --process $$
```

## Build e Distribuição

### Build com Meson

```bash
# Configurar
meson setup builddir --prefix=/usr

# Compilar
meson compile -C builddir

# Instalar
sudo meson install -C builddir

# Desinstalar
sudo ninja -C builddir uninstall
```

### Criar Pacote Debian

```bash
# TODO: Adicionar suporte para dpkg-buildpackage
```

### Criar Flatpak

```bash
# TODO: Adicionar manifest flatpak
```

## Recursos Adicionais

- [GTK4 Documentation](https://docs.gtk.org/gtk4/)
- [libadwaita Documentation](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- [Python GObject Introspection](https://pygobject.readthedocs.io/)
- [PolicyKit Documentation](https://www.freedesktop.org/software/polkit/docs/)
- [xrdp Documentation](https://github.com/neutrinolabs/xrdp)
