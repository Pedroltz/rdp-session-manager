# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [0.2.0] - 2025-10-18

### 🎉 Release com Funcionalidades Críticas

Esta versão adiciona funcionalidades essenciais que tornam a aplicação totalmente utilizável:
- Exclusão inteligente de usuários com encerramento automático de sessões
- Sistema completo de gerenciamento de FreeRDP
- Dialog visual para credenciais RDP
- Verificação e instalação automática de xrdp
- Sistema de logs completo capturando todos os módulos

### Adicionado
- ✨ **Exclusão Inteligente de Usuários**
  - Detecção automática de processos ativos (`get_user_processes()`)
  - Encerramento graceful de processos (SIGTERM) antes de deletar
  - Encerramento forçado (SIGKILL) se processos não encerrarem
  - Dialog de aviso especial quando usuário está conectado
  - Remoção completa de dados (conta, home, configs, processos)

- ✨ **Gerenciamento Completo de FreeRDP**
  - Detecção automática se FreeRDP está instalado
  - Verificação usando `shutil.which('xfreerdp3')` e `shutil.which('xfreerdp')`
  - Dialog oferecendo instalação quando FreeRDP não encontrado
  - Instalação automática de `freerdp3-x11` via pkexec
  - Progresso visual durante instalação
  - Suporte para xfreerdp3 e xfreerdp (fallback)

- ✨ **Dialog Visual para Credenciais RDP**
  - Interface gráfica para entrada de credenciais
  - Campo de domínio (opcional) para domínios Windows
  - Campo de senha com caracteres ocultos
  - Navegação com Enter (domínio → senha → conectar)
  - Validação de senha obrigatória
  - Credenciais passadas via parâmetros `/d:` e `/p:`

- ✨ **Verificação e Instalação de xrdp**
  - Verificação automática de xrdp ao iniciar aplicação
  - Banner de aviso no topo se xrdp não instalado
  - Botão "Instalar Agora" no banner
  - Dialog com progresso visual para instalação
  - Instalação de `xrdp` e `xorgxrdp`
  - Habilitação e inicialização automática do serviço
  - Atualização periódica do status (a cada 10 segundos)
  - Bloqueio de criação de usuários se xrdp não instalado

- ✨ **Sistema de Logs Completo**
  - Configuração do ROOT logger para capturar todos os módulos
  - Logs de `core.user_manager`, `core.rdp_config`, `core.de_installer`
  - Logs de `core.system_deps`, `core.session_monitor`
  - Logs de `ui.main_window`, `ui.user_dialog`
  - Logs centralizados em arquivo único
  - Rotação automática de logs (10MB, 5 backups)

- ✨ **Detecção Dinâmica de Desktop Environment**
  - Leitura automática do arquivo `.xsession` para detectar DE real
  - Mapeamento de comandos de startup para identificadores DE
  - Detecção de LXDE, LXQt, XFCE, MATE, Cinnamon, GNOME, KDE
  - Cálculo automático de portas RDP baseado em UID
  - Exibição correta do DE na interface (não mais hardcoded "xfce")

- 📄 **Documentação Atualizada**
  - README.md totalmente reescrito com todas as features
  - STATUS.md com testes realizados e estatísticas
  - CHANGELOG.md estruturado e detalhado
  - Instruções de uso passo a passo
  - Screenshots em ASCII art dos dialogs

### Corrigido
- 🔧 **pkexec com Caminhos Absolutos** (Crítico)
  - **Problema**: Comandos falhando com código 127 "command not found"
  - **Causa**: pkexec não tem `/usr/sbin` no PATH
  - **Solução**: Todos os comandos agora usam caminhos completos:
    - `/usr/sbin/groupadd`
    - `/usr/sbin/useradd`
    - `/usr/sbin/userdel`
    - `/usr/sbin/chpasswd`
    - `/usr/bin/apt-get`
    - `/usr/bin/systemctl`
    - `/usr/bin/mkdir`
    - `/usr/bin/chmod`
    - `/usr/bin/pkill`
    - `/usr/bin/bash`
    - `/usr/bin/cp`
    - `/usr/bin/chown`

- 🔧 **Campo de Senha com Problemas de Foco**
  - **Problema**: Foco retornava automaticamente para senha, impossibilitando digitar no domínio
  - **Causa**: `GLib.timeout_add()` roubando foco continuamente
  - **Solução**: Removido timeout, adicionado `set_can_focus(True)` em ambos os campos

- 🔧 **Apenas Um Caractere no Campo de Senha**
  - **Problema**: `Adw.PasswordEntryRow` não funcionava dentro de `Adw.MessageDialog`
  - **Solução**: Substituído por `Gtk.Entry()` com `set_visibility(False)`

- 🔧 **Erro ao Deletar Usuário Conectado**
  - **Problema**: "user is currently used by process XXXX"
  - **Solução**: Implementado encerramento automático de processos antes de deletar

- 🔧 **Todos Usuários Apareciam como XFCE**
  - **Problema**: Interface mostrava "XFCE • Porta 3389" para todos, independente do DE escolhido
  - **Causa**: Valores hardcoded em `list_users()` (`desktop_env="xfce"`, `rdp_port=3389`)
  - **Solução**: Implementado detecção dinâmica lendo `.xsession` e calculando porta pelo UID

- 🔧 **Desktop Environment Aparecia como "Desconhecida"**
  - **Problema**: Mesmo após implementar detecção, DE aparecia como "Desconhecida"
  - **Causa**: Permissões 700 no home directory impediam leitura do `.xsession`
  - **Solução**: Home directory criado com permissões 751 (rwxr-x--x) permitindo acesso ao .xsession

### Melhorado
- 🎨 **Confirmação de Exclusão Contextual**
  - Dois tipos de dialog dependendo do estado do usuário:
    - **Usuário inativo**: Lista detalhada do que será removido
    - **Usuário ativo**: Aviso sobre encerramento de sessões
  - Botões mais descritivos: "Encerrar e Remover" vs "Remover"

- 🎨 **Feedback Visual Aprimorado**
  - Toast "Encerrando sessões..." quando usuário está conectado
  - Toast "Removendo usuário..." quando usuário está inativo
  - Dialog de erro detalhado em caso de falha
  - Logs detalhados de cada etapa da exclusão

- ⚡ **Conexão RDP Simplificada**
  - Apenas 3 cliques para conectar:
    1. Botão de rede no card
    2. "Abrir FreeRDP"
    3. Digite senha e "Conectar"
  - Domínio opcional para usuários sem Active Directory
  - Tratamento de erros mais amigável

### Segurança
- 🔒 **Validação de Processos**
  - Verificação de processos ativos antes de deletar
  - Uso de `pgrep -u` para listar PIDs
  - Encerramento graceful antes de forçar

- 🔒 **Comandos com Caminhos Absolutos**
  - Previne path injection
  - Garante execução dos comandos corretos
  - Compatibilidade com diferentes distribuições

### Arquivos Modificados

#### Core
- `src/core/user_manager.py`:
  - Adicionado `get_user_processes(username) -> List[int]`
  - Adicionado `kill_user_processes(username, force=False) -> bool`
  - Modificado `delete_user()` para aceitar `kill_processes=True`
  - Adicionado `_detect_desktop_env(home_dir) -> str` para detectar DE do .xsession
  - Adicionado `_detect_rdp_port(uid) -> int` para calcular porta baseada em UID
  - Modificado `list_users()` para usar detecção dinâmica ao invés de valores hardcoded
  - Atualizado todos os comandos para caminhos absolutos

- `src/core/system_deps.py`:
  - Adicionado gerenciamento de FreeRDP em `REQUIRED_PACKAGES`
  - Adicionado `is_freerdp_installed() -> bool`
  - Adicionado `get_freerdp_command() -> str`
  - Atualizado todos os comandos para caminhos absolutos

- `src/core/rdp_config.py`:
  - Atualizado comandos para caminhos absolutos

- `src/core/de_installer.py`:
  - Atualizado comandos para caminhos absolutos

#### UI
- `src/ui/main_window.py`:
  - Modificado `on_delete_user()` para verificar processos ativos
  - Modificado `confirm_delete_user()` para encerrar processos
  - Adicionado `show_password_dialog(user)` para credenciais visuais
  - Adicionado `on_password_dialog_response()` para processar credenciais
  - Modificado `launch_freerdp_client()` para aceitar domínio
  - Adicionado `handle_connect_response()` para verificar FreeRDP
  - Adicionado `on_freerdp_install_response()` para instalar FreeRDP
  - Adicionado `create_xrdp_warning_banner()` para banner de aviso
  - Adicionado `update_xrdp_status()` para verificação periódica
  - Adicionado `on_install_xrdp_clicked()` para instalação de xrdp

- `src/application.py`:
  - Adicionado `show_xrdp_install_dialog()` para instalação com progresso
  - Adicionado `install_freerdp_with_progress()` para FreeRDP

#### Utils
- `src/utils/logger.py`:
  - Modificado `setup_logger()` para configurar ROOT logger
  - Agora captura logs de TODOS os módulos

### Documentação
- 📚 `README.md`: Reescrito completamente com todas as funcionalidades
- 📚 `STATUS.md`: Atualizado com testes e estatísticas da v0.2.0
- 📚 `CHANGELOG.md`: Este arquivo
- 📚 `FIXES.md`: Documentação das correções aplicadas

### Testes
- ✅ Criação de usuário: **PASSOU**
- ✅ Exclusão de usuário inativo: **PASSOU**
- ✅ Exclusão de usuário com 58 processos ativos: **PASSOU**
- ✅ Conexão RDP com credenciais visuais: **PASSOU**
- ✅ Instalação automática de FreeRDP: **PASSOU**
- ✅ Instalação automática de xrdp: **PASSOU**
- ✅ Sistema de logs completo: **PASSOU**

---

## [0.1.0] - 2025-10-17

### 🎉 Release Inicial

Primeira versão funcional do RDP Session Manager com todas as funcionalidades base implementadas.

### Adicionado
- ✅ Interface GTK4 com libadwaita
- ✅ Gerenciamento de usuários RDP
- ✅ Criação de usuários com validação
- ✅ Suporte para 7 Desktop Environments:
  - LXDE, LXQt, XFCE, MATE, Cinnamon, GNOME, KDE Plasma
- ✅ Instalação automática de Desktop Environments
- ✅ Sistema de logs e auditoria
- ✅ PolicyKit para operações administrativas
- ✅ Sistema de backup e restauração
- ✅ Testes unitários
- ✅ Documentação completa
- ✅ Monitoramento de sessões ativas
- ✅ Toast notifications para feedback
- ✅ Empty state quando não há usuários
- ✅ Botão de conexão RDP em cada card
- ✅ Cópia automática de IP para clipboard

### Corrigido
- 🔧 Versão do libadwaita de '1.0' para '1' (Debian 13)
- 🔧 `Gtk.Widget.get_default_display()` substituído por `Gdk.Display.get_default()`
- 🔧 Erro `psutil.process_iter(['connections'])` corrigido usando `proc.connections()`
- 🔧 Adicionado `python3-psutil` às dependências

### Avisos
- ⚠️ Grupo `rdp-users` precisa ser criado manualmente (corrigido em v0.2.0)
- ⚠️ Warnings do GTK sobre medição de labels são cosméticos
- ⚠️ Templates GTK podem mostrar avisos de binding - não afeta operação

### Compatibilidade Testada
- Debian 13 (Trixie)
- GTK 4.18.6
- libadwaita 1.7.6
- Python 3.13

---

## [Unreleased]

### Planejado para v0.3.0
- [ ] Quotas de disco por usuário
- [ ] Limites de recursos (CPU/RAM) por sessão com cgroups
- [ ] AppArmor profiles restritivos
- [ ] Auditoria de ações em tempo real
- [ ] Backup automático diário

### Planejado para v0.4.0
- [ ] Pool de portas RDP gerenciado
- [ ] Async UI para melhor responsividade
- [ ] Cache de operações
- [ ] Otimizações de rede RDP
- [ ] Dashboard de uso de recursos

### Planejado para v1.0.0
- [ ] Autenticação via LDAP/Active Directory
- [ ] Interface web de administração
- [ ] API REST
- [ ] Suporte para clustering/balanceamento
- [ ] Templates de configuração
- [ ] Integração com Cockpit
- [ ] Métricas e dashboards avançados

---

## Formato do Changelog

### Tipos de Mudanças
- `Adicionado` para novas funcionalidades
- `Modificado` para mudanças em funcionalidades existentes
- `Descontinuado` para funcionalidades que serão removidas
- `Removido` para funcionalidades removidas
- `Corrigido` para correções de bugs
- `Segurança` para vulnerabilidades corrigidas
- `Melhorado` para otimizações e melhorias

### Emojis Usados
- ✨ Nova feature
- 🔧 Correção de bug
- 🎨 Melhorias de UI/UX
- ⚡ Melhorias de performance
- 🔒 Segurança
- 📚 Documentação
- ✅ Testes
- ⚠️ Avisos importantes
- 🎉 Releases e marcos importantes

---

**Links**:
- [README](README.md)
- [STATUS](STATUS.md)
- [FIXES](FIXES.md)
- [Documentação](docs/)

**Mantenedor**: Pedro L. Tunin
**Última Atualização**: 2025-10-18
