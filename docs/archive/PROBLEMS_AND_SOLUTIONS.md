# Problemas Conhecidos e Soluções

## Problemas Atuais e Futuros Antecipados

### 1. 🔴 Conflitos de Porta RDP

**Problema**: Múltiplos usuários podem tentar usar a mesma porta RDP.

**Impacto**: Alto - Impede criação de novos usuários

**Causas Possíveis**:
- Sistema não verifica portas em uso adequadamente
- Configuração de porta manual conflitante
- Processos xrdp antigos ainda ocupando portas

**Soluções**:

**Curto Prazo**:
```python
# Implementar verificação mais robusta em rdp_config.py
def is_port_available(self, port: int) -> bool:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False
```

**Longo Prazo**:
- Implementar pool de portas gerenciado
- Adicionar range configurável de portas RDP
- Criar sistema de alocação dinâmica

---

### 2. 🟡 Permissões de Diretórios Home Customizados

**Problema**: Criação de usuários RDP em `/opt/rdp-users` pode falhar por permissões.

**Impacto**: Médio - Usuários não podem ser criados

**Causas Possíveis**:
- Diretório `/opt/rdp-users` não existe
- Permissões incorretas no diretório pai
- SELinux/AppArmor bloqueando acesso

**Soluções**:

**Imediato**:
```bash
# Script de configuração inicial
sudo mkdir -p /opt/rdp-users
sudo chmod 755 /opt/rdp-users
sudo chown root:rdp-users /opt/rdp-users
```

**Futuro**:
- Verificar e criar diretório automaticamente no primeiro uso
- Adicionar verificação de permissões no startup
- Suportar diretórios alternativos configuráveis

---

### 3. 🟡 Compatibilidade entre Desktop Environments

**Problema**: Alguns DEs não funcionam bem via RDP.

**Impacto**: Médio - Experiência ruim do usuário

**DEs Problemáticos**:
- **GNOME**: Wayland não funciona via RDP (requer X11)
- **KDE Plasma**: Pode ter problemas de performance
- **Cinnamon**: Efeitos visuais causam lag

**Soluções**:

**Para GNOME**:
```bash
# Forçar X11 ao invés de Wayland
echo "export GDM_BACKEND=x11" >> /opt/rdp-users/user/.xsessionrc
```

**Para KDE**:
```bash
# Desabilitar compositing
echo "export KWIN_COMPOSE=N" >> ~/.config/startupconfig
```

**Recomendação**: Usar XFCE ou MATE para melhor experiência RDP.

---

### 4. 🔴 Gerenciamento de Memória com Múltiplas Sessões

**Problema**: Servidor fica lento com muitas sessões RDP ativas.

**Impacto**: Alto - Performance degradada

**Causas**:
- Cada DE consome 500MB-2GB de RAM
- Processos não são terminados corretamente ao desconectar
- Sem limite de recursos por sessão

**Soluções**:

**Imediato**:
```bash
# Limitar recursos com systemd
cat > /etc/systemd/system/user-rdp@.service << EOF
[Service]
User=%i
MemoryMax=1G
CPUQuota=50%
IOWeight=100
EOF
```

**Futuro**:
- Implementar cgroups para cada sessão
- Auto-kill de sessões inativas
- Dashboard de uso de recursos
- Alertas de limite de recursos

---

### 5. 🟡 Segurança: Isolamento de Usuários RDP

**Problema**: Usuários RDP podem acessar recursos do sistema.

**Impacto**: Médio - Risco de segurança

**Riscos**:
- Acesso a arquivos do sistema
- Instalação de software não autorizado
- Consumo excessivo de recursos

**Soluções**:

**Imediato**:
```bash
# Criar profile AppArmor restritivo
sudo aa-genprof /bin/bash
# Configurar em modo "complain" inicialmente
```

**Longo Prazo**:
- Implementar quotas de disco por usuário
- Restringir comandos sudo
- Sandbox com namespaces/containers
- Auditoria de ações em tempo real

---

### 6. 🟠 Performance de Rede

**Problema**: Conexões RDP lentas em redes com alta latência.

**Impacto**: Médio - Experiência ruim do usuário

**Otimizações Necessárias**:

```ini
# /etc/xrdp/xrdp.ini
[Globals]
tcp_nodelay=true
tcp_keepalive=true

# Compressão
bitmap_compression=true
bulk_compression=true

# Codec
max_bpp=24
```

**Futuro**:
- Implementar perfis de conexão (LAN, WAN, Móvel)
- Auto-ajuste de qualidade baseado em latência
- Suporte para RemoteFX

---

### 7. 🔴 Falhas na Instalação de Desktop Environments

**Problema**: Instalação de DE pode falhar e deixar sistema inconsistente.

**Impacto**: Alto - Sistema instável

**Causas**:
- Dependências não resolvidas
- Espaço em disco insuficiente
- Timeout durante download
- Conflitos de pacotes

**Soluções**:

**Prevenção**:
```python
def install_de_safe(self, de_id):
    # 1. Verificar espaço em disco
    if not self.check_disk_space(de_id):
        return False, "Insufficient disk space"

    # 2. Simular instalação
    result = subprocess.run(['apt-get', 'install', '-s'] + packages)
    if result.returncode != 0:
        return False, "Dependency conflicts"

    # 3. Criar ponto de restauração
    self.create_snapshot()

    # 4. Instalar com retry
    for attempt in range(3):
        if self.install_de(de_id):
            return True, "Success"
        time.sleep(5)

    # 5. Rollback se falhar
    self.restore_snapshot()
    return False, "Installation failed"
```

---

### 8. 🟠 Logs e Auditoria

**Problema**: Logs crescem indefinidamente.

**Impacto**: Baixo - Uso excessivo de disco

**Soluções**:

**Rotação Automática**:
```python
# Em logger.py - já implementado
RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

**Limpeza Periódica**:
```python
# Adicionar ao cron
@daily
find /var/log/rdp-session-manager/ -name "*.log.*" -mtime +30 -delete
```

---

### 9. 🔴 Backup e Recuperação

**Problema**: Não há backup automático de configurações.

**Impacto**: Alto - Perda de dados em caso de falha

**Implementação Necessária**:

```python
# Backup automático diário
class AutoBackup:
    def __init__(self):
        self.backup_manager = BackupManager()
        GLib.timeout_add_seconds(86400, self.daily_backup)

    def daily_backup(self):
        users = self.user_manager.list_users()
        for user in users:
            self.backup_manager.create_backup(user.to_dict())
        return True  # Continue timer
```

---

### 10. 🟡 Escalabilidade

**Problema**: Sistema não escala bem para muitos usuários.

**Impacto**: Médio - Limitação de crescimento

**Limitações Atuais**:
- Sem clustering
- Sem balanceamento de carga
- Gerenciamento manual de portas
- UI sincr

ona (trava com muitos usuários)

**Soluções Futuras**:

1. **Async UI**:
```python
async def load_users(self):
    users = await self.user_manager.list_users_async()
    # Update UI
```

2. **Clustering**:
- Implementar backend distribuído
- Balanceamento de carga entre servidores
- Sincronização de configurações

3. **Database**:
- Migrar de arquivos para PostgreSQL/SQLite
- Cache com Redis
- API REST para múltiplos frontends

---

## Matriz de Prioridades

| Problema | Impacto | Esforço | Prioridade |
|----------|---------|---------|------------|
| Conflitos de Porta | Alto | Baixo | **P0 - Crítico** |
| Múltiplas Sessões (RAM) | Alto | Médio | **P0 - Crítico** |
| Backup Automático | Alto | Baixo | **P1 - Alto** |
| Isolamento Segurança | Médio | Alto | **P1 - Alto** |
| Instalação DE | Alto | Médio | **P1 - Alto** |
| Permissões Home Dir | Médio | Baixo | **P2 - Médio** |
| Compat. DEs | Médio | Médio | **P2 - Médio** |
| Performance Rede | Médio | Alto | **P2 - Médio** |
| Logs Crescentes | Baixo | Baixo | **P3 - Baixo** |
| Escalabilidade | Médio | Alto | **P3 - Longo Prazo** |

## Checklist de Melhorias

### Curto Prazo (1-2 semanas)
- [ ] Implementar pool de portas RDP
- [ ] Adicionar verificação de espaço em disco
- [ ] Criar script de setup inicial
- [ ] Implementar backup automático
- [ ] Adicionar limites de recursos com cgroups

### Médio Prazo (1-2 meses)
- [ ] Sistema de quotas de disco
- [ ] Profile AppArmor restritivo
- [ ] Otimizações de performance RDP
- [ ] Retry logic para instalação de DEs
- [ ] Async UI para melhor responsividade

### Longo Prazo (3-6 meses)
- [ ] Backend com database
- [ ] API REST
- [ ] Interface Web
- [ ] Suporte a clustering
- [ ] Integração com LDAP/AD

## Como Reportar Problemas

1. **Verifique** se o problema já está listado
2. **Colete** logs relevantes:
   ```bash
   journalctl -u xrdp > xrdp.log
   cat ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log > app.log
   ```
3. **Abra Issue** no GitHub com:
   - Descrição do problema
   - Passos para reproduzir
   - Logs anexados
   - Versão do sistema e aplicação

## Contribuindo com Soluções

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para guidelines de contribuição.
