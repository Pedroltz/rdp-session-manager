# RDP Session Manager

> Gerenciador completo de sessões RDP com interface GTK4 para GNOME

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![GTK](https://img.shields.io/badge/GTK-4.0-green.svg)
![Status](https://img.shields.io/badge/status-✅_Funcional-success)

## 📋 Descrição

RDP Session Manager é uma aplicação moderna e completa para GNOME que permite criar, gerenciar e monitorar sessões RDP de forma fácil e intuitiva. Com interface GTK4 e integração completa com o ecossistema GNOME, o aplicativo oferece gerenciamento profissional de usuários RDP com segurança e facilidade.

### Destaques

- **Interface Moderna**: GTK4 com libadwaita para integração perfeita com GNOME
- **Gerenciamento Completo**: Criação, exclusão e monitoramento de usuários RDP
- **Instalação Automática**: Instala automaticamente xrdp, FreeRDP e ambientes desktop
- **Conexão Visual**: Dialog gráfico para inserir credenciais e conectar
- **Segurança Integrada**: PolicyKit para todas operações administrativas
- **Exclusão Inteligente**: Encerra sessões ativas automaticamente ao deletar usuários

## ✨ Funcionalidades

### Gerenciamento de Usuários
- ✅ Criar usuários RDP com configuração automática
- ✅ Excluir usuários com remoção completa de dados
- ✅ Encerramento automático de sessões ativas ao deletar
- ✅ Validação de dados em tempo real
- ✅ Detecção de processos ativos por usuário
- ✅ Visualização de status (Ativo/Inativo)

### Ambientes Desktop
- ✅ Suporte para 7 Desktop Environments:
  - LXDE (250MB) - Ultra leve
  - LXQt (350MB) - Leve e moderno
  - XFCE (400MB) - **Recomendado**
  - MATE (600MB) - Clássico
  - Cinnamon (800MB) - Elegante
  - GNOME (1.2GB) - Completo
  - KDE Plasma (1.5GB) - Poderoso
- ✅ Instalação automática de ambientes desktop
- ✅ Verificação de espaço em disco antes de instalar
- ✅ Detecção automática de DEs já instalados

### Conexão RDP
- ✅ **Detecção automática de FreeRDP** instalado
- ✅ **Instalação automática de FreeRDP** com progresso visual
- ✅ **Dialog visual para credenciais** (domínio e senha)
- ✅ **Lançamento direto do cliente RDP** com um clique
- ✅ Suporte para domínios Windows
- ✅ Cópia automática de endereço para clipboard
- ✅ Instruções para clientes Windows e Linux

### Dependências do Sistema
- ✅ **Verificação automática de xrdp** ao iniciar
- ✅ **Banner de aviso** se xrdp não estiver instalado
- ✅ **Instalação automática de xrdp** com um clique
- ✅ Progresso visual em tempo real
- ✅ Verificação de FreeRDP e instalação sob demanda

### Monitoramento e Logs
- ✅ Monitoramento de sessões ativas em tempo real
- ✅ Visualização de IP do servidor e porta RDP
- ✅ Sistema de logs completo e estruturado
- ✅ Logs de todos os módulos centralizados
- ✅ Rotação automática de logs

### Segurança
- ✅ Integração com PolicyKit para operações administrativas
- ✅ Usuários isolados em grupo `rdp-users`
- ✅ UIDs começam em 5000 (fora da faixa normal)
- ✅ Home directories em `/opt/rdp-users`
- ✅ Validação de senhas fortes
- ✅ Comandos executados com caminhos absolutos

## 🚀 Instalação

### Dependências Obrigatórias

#### Debian/Ubuntu:
```bash
sudo apt install python3 python3-pip python3-gi \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    libgirepository1.0-dev gcc libcairo2-dev \
    pkg-config python3-dev python3-psutil \
    meson ninja-build
```

### Dependências Opcionais (instaláveis pela aplicação)
```bash
# xrdp - Servidor RDP (pode ser instalado pela aplicação)
sudo apt install xrdp xorgxrdp

# FreeRDP - Cliente RDP (pode ser instalado pela aplicação)
sudo apt install freerdp3-x11
```

### Instalação da Aplicação

#### Método 1: Executar Direto (Desenvolvimento)
```bash
# Clone o repositório
git clone https://github.com/yourusername/rdp-session-manager.git
cd rdp-session-manager

# Instale dependências Python
pip install -r requirements.txt

# Execute
./run.sh
# ou
python3 src/main.py
```

#### Método 2: Instalação via Meson
```bash
# Configure e compile
meson setup builddir
meson compile -C builddir

# Instale no sistema
sudo meson install -C builddir

# Execute
rdp-session-manager
```

## 🎯 Uso

### Primeiro Uso

1. **Inicie a aplicação**:
   ```bash
   rdp-session-manager
   ```

2. **Instale o xrdp** (se não estiver instalado):
   - Um banner aparecerá no topo da janela
   - Clique em "Instalar Agora"
   - Autentique com sua senha quando solicitado
   - Aguarde a instalação concluir

### Criar um Usuário RDP

1. Clique no botão **"+"** na barra superior
2. Preencha os dados:
   - **Nome de usuário**: letras minúsculas, números, - e _
   - **Nome completo**: nome real do usuário
   - **Senha**: mínimo 8 caracteres, letras e números
   - **Confirmar senha**
3. Escolha o **ambiente desktop** (XFCE recomendado)
4. Configure a **porta RDP** (ou deixe automático em 3389)
5. Marque **"Instalar ambiente desktop"** se ainda não estiver instalado
6. Clique em **"Criar"**
7. Autentique quando solicitado (PolicyKit)
8. Aguarde a criação (pode levar alguns minutos se instalar DE)

### Conectar via RDP

#### Opção 1: Usando a Aplicação (Recomendado)

1. Clique no botão de **rede** no card do usuário
2. Clique em **"Abrir FreeRDP"**
3. Se FreeRDP não estiver instalado:
   - Dialog perguntará se deseja instalar
   - Clique em "Instalar FreeRDP"
   - Aguarde a instalação
4. Digite o **domínio** (opcional para domínios Windows)
5. Digite a **senha** do usuário
6. Clique em **"Conectar"**
7. A sessão RDP abrirá automaticamente!

#### Opção 2: Cliente Manual

```bash
# Linux (FreeRDP)
xfreerdp3 /v:<IP_DO_SERVIDOR>:3389 /u:<USUARIO> /cert:ignore

# Windows (Remote Desktop Connection)
# Digite no cliente: <IP_DO_SERVIDOR>:3389
```

### Excluir um Usuário

1. Clique no botão de **lixeira** no card do usuário
2. Se o usuário estiver **conectado**:
   - Dialog avisará que sessões serão encerradas
   - Clique em "Encerrar e Remover"
3. Se o usuário estiver **inativo**:
   - Confirme a exclusão
   - Clique em "Remover"
4. Autentique quando solicitado
5. **TODOS os dados serão removidos**:
   - ✓ Conta de usuário
   - ✓ Diretório home completo
   - ✓ Arquivos pessoais
   - ✓ Configurações RDP
   - ✓ Processos ativos encerrados

## 📁 Estrutura do Projeto

```
RemoteApps-RDP/
├── src/
│   ├── core/                    # Módulos principais
│   │   ├── user_manager.py      # Gerenciamento de usuários
│   │   ├── rdp_config.py        # Configuração RDP
│   │   ├── de_installer.py      # Instalador de DEs
│   │   ├── system_deps.py       # Gerenciamento de dependências
│   │   └── session_monitor.py   # Monitor de sessões
│   ├── ui/                      # Interface GTK4
│   │   ├── main_window.py       # Janela principal
│   │   └── user_dialog.py       # Diálogo de criação
│   ├── utils/                   # Utilitários
│   │   ├── logger.py            # Sistema de logs
│   │   ├── validator.py         # Validação de entrada
│   │   └── backup.py            # Sistema de backup
│   ├── application.py           # Aplicação principal
│   └── main.py                  # Entry point
├── data/
│   ├── ui/                      # Arquivos .ui GTK
│   │   ├── main-window.ui
│   │   └── user-dialog.ui
│   └── com.rdp.SessionManager.desktop
├── docs/                        # Documentação
│   ├── DEVELOPMENT.md
│   ├── PROBLEMS_AND_SOLUTIONS.md
│   └── PROJECT_SUMMARY.md
├── tests/                       # Testes unitários
├── README.md                    # Este arquivo
├── STATUS.md                    # Status do projeto
├── CHANGELOG.md                 # Histórico de mudanças
└── FIXES.md                     # Correções aplicadas
```

## 🔒 Segurança

### PolicyKit (pkexec)

A aplicação usa PolicyKit para executar operações administrativas de forma segura:

- **Criação de usuários**: `pkexec /usr/sbin/useradd`
- **Exclusão de usuários**: `pkexec /usr/sbin/userdel`
- **Gerenciamento de grupos**: `pkexec /usr/sbin/groupadd`
- **Instalação de pacotes**: `pkexec /usr/bin/apt-get`
- **Encerramento de processos**: `pkexec /usr/bin/pkill`

> O usuário será solicitado a autenticar quando necessário.

### Isolamento de Usuários

- Usuários RDP criados em grupo separado (`rdp-users`)
- UIDs começam em 5000 (fora da faixa de usuários normais 1000-4999)
- Home directories isolados em `/opt/rdp-users/`
- Cada usuário tem porta RDP dedicada (3389+)

### Validação e Sanitização

- Nomes de usuário: `^[a-z][a-z0-9_-]{2,31}$`
- Senhas fortes: mínimo 8 caracteres, letras e números
- Portas RDP: verificação de disponibilidade
- Caminhos absolutos em todos os comandos do sistema

## 📊 Monitoramento e Logs

### Localização dos Logs

```bash
# Logs da aplicação
~/.local/share/rdp-session-manager/logs/rdp-session-manager.log

# Logs do xrdp
/var/log/xrdp/

# Ver logs em tempo real
tail -f ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log
```

### Sistema de Logs

O sistema de logs captura **TODOS os módulos** da aplicação:

```
2025-10-18 00:46:47 - core.user_manager - INFO - Removendo usuário RDP: trix_bastardo
2025-10-18 00:46:47 - core.user_manager - INFO - Usuário trix_bastardo tem 58 processos ativos
2025-10-18 00:46:47 - core.user_manager - INFO - Terminando processos...
2025-10-18 00:46:55 - core.user_manager - INFO - ✓ Usuário removido com sucesso
```

Logs incluem:
- Operações de criação/exclusão de usuários
- Instalação de pacotes e DEs
- Conexões RDP
- Erros e avisos
- Processos encerrados

## 🐛 Problemas Conhecidos e Soluções

### xrdp não está instalado

**Sintoma**: Banner de aviso no topo da janela

**Solução**:
1. Clique em "Instalar Agora" no banner
2. Ou instale manualmente: `sudo apt install xrdp xorgxrdp`

### FreeRDP não está instalado

**Sintoma**: Ao clicar em "Abrir FreeRDP", aparece dialog de instalação

**Solução**:
1. Clique em "Instalar FreeRDP" no dialog
2. Ou instale manualmente: `sudo apt install freerdp3-x11`

### Não consigo deletar usuário conectado

**Sintoma**: "user is currently used by process"

**Solução**:
- A aplicação agora encerra processos automaticamente!
- Apenas confirme "Encerrar e Remover" no dialog

### Ambiente desktop não inicia

**Sintoma**: Conexão RDP estabelecida mas tela preta

**Solução**:
1. Verifique logs: `tail /var/log/xrdp/xrdp.log`
2. Teste manualmente: `su - usuario -c "startxfce4"`
3. Reinstale o DE pela aplicação

### Porta RDP em uso

**Sintoma**: Erro ao criar usuário - porta já em uso

**Solução**:
- O aplicativo detecta automaticamente e usa a próxima porta disponível
- Verifique se não há conflitos com firewall

## 🔮 Roadmap

### ✅ Implementado (v0.2.0)
- [x] Detecção automática de FreeRDP
- [x] Instalação automática de FreeRDP
- [x] Dialog visual para credenciais
- [x] Exclusão de usuários com sessões ativas
- [x] Encerramento automático de processos
- [x] Sistema de logs completo
- [x] Banner de aviso para xrdp

### 📋 Próximas Versões

#### v0.3.0 - Melhorias de Segurança
- [ ] Quotas de disco por usuário
- [ ] Limite de recursos (CPU/RAM) por sessão
- [ ] AppArmor profiles restritivos
- [ ] Auditoria de ações em tempo real

#### v0.4.0 - Performance e Escalabilidade
- [ ] Pool de portas RDP gerenciado
- [ ] Async UI para múltiplos usuários
- [ ] Cache de operações
- [ ] Otimizações de rede RDP

#### v1.0.0 - Enterprise Features
- [ ] Autenticação via LDAP/Active Directory
- [ ] Interface web de administração
- [ ] API REST
- [ ] Suporte para clustering
- [ ] Templates de configuração
- [ ] Dashboards e métricas

## 🧪 Testes

Execute os testes unitários:

```bash
# Usando pytest
pytest tests/ -v

# Ou usando o script
./tests/run_tests.sh
```

## 📝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a GNU General Public License v3.0 - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Autores

- **Pedro L. Tunin** - *Desenvolvimento* - [trix](https://github.com/trix)

## 🙏 Agradecimentos

- Comunidade GNOME pelo GTK4 e libadwaita
- Projeto xrdp e FreeRDP
- Comunidade Debian/Linux
- Todos os contribuidores

## 📞 Suporte

- 📚 Documentação: [docs/](docs/)
- 🐛 Bugs: Abra uma issue no GitHub
- 💬 Discussões: Use GitHub Discussions
- 📋 Status: Veja [STATUS.md](STATUS.md)

---

**Desenvolvido com ❤️ para a comunidade GNOME/Linux**

**Versão Atual**: 0.2.0
**Status**: ✅ Totalmente Funcional
**Última Atualização**: 2025-10-18
