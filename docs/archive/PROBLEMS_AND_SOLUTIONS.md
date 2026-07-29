# Known Issues and Solutions

## Current and Anticipated Future Problems

### 1. 🔴 RDP Port Conflicts

**Issue**: Multiple users may attempt to use the same RDP port.

**Impact**: High - Prevents the creation of new users

**Possible Causes**:
- System does not check ports in use properly
- Conflicting manual port configuration
- Old xrdp processes still occupying ports

**Solutions**:

**Curto Prazo**:
```python
# Implement more robust checking in rdp_config.py
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
- Implement managed port pool
- Add configurable range of RDP ports
- Create dynamic allocation system

---

### 2. 🟡 Custom Home Directory Permissions

**Issue**: Creating RDP users on `/opt/rdp-users` may fail due to permissions.

**Impact**: Medium - Users cannot be created

**Possible Causes**:
- Directory `/opt/rdp-users` does not exist
- Incorrect permissions on the parent directory
- SELinux/AppArmor bloqueando acesso

**Solutions**:

**Imediato**:
```bash
# Initial configuration script
sudo mkdir -p /opt/rdp-users
sudo chmod 755 /opt/rdp-users
sudo chown root:rdp-users /opt/rdp-users
```

**Futuro**:
- Automatically scan and create directory on first use
- Add permissions check on startup
- Support configurable alternative directories

---

### 3. 🟡 Compatibility between Desktop Environments

**Problem**: Some DEs do not work well via RDP.

**Impact**: Medium - Poor user experience

**Problematic DEs**:
- **GNOME**: Wayland does not work via RDP (requires X11)
- **KDE Plasma**: May have performance issues
- **Cinnamon**: Efeitos visuais causam lag

**Solutions**:

**For GNOME**:
```bash
# Force X11 instead of Wayland
echo "export GDM_BACKEND=x11" >> /opt/rdp-users/user/.xsessionrc
```

**For KDE**:
```bash
# Disable compositing
echo "export KWIN_COMPOSE=N" >> ~/.config/startupconfig
```

**Recommendation**: Use XFCE or MATE for better RDP experience.

---

### 4. 🔴 Memory Management with Multiple Sessions

**Problem**: Server becomes slow with many active RDP sessions.

**Impacto**: Alto - Performance degradada

**Causas**:
- Each DE consumes 500MB-2GB of RAM
- Processes are not terminated correctly when disconnecting
- No resource limit per session

**Solutions**:

**Imediato**:
```bash
# Limit resources with systemd
cat > /etc/systemd/system/user-rdp@.service << EOF
[Service]
User=%i
MemoryMax=1G
CPUQuota=50%
IOWeight=100
EOF
```

**Futuro**:
- Implement cgroups for each session
- Auto-kill of inactive sessions
- Resource usage dashboard
- Resource limit alerts

---

### 5. 🟡 Security: RDP User Isolation

**Issue**: RDP users can access system resources.

**Impact**: Medium - Security risk

**Riscos**:
- Access to system files
- Installation of unauthorized software
- Excessive consumption of resources

**Solutions**:

**Imediato**:
```bash
# Create restrictive AppArmor profile
sudo aa-genprof /bin/bash
# Configure in "complain" mode initially
```

**Longo Prazo**:
- Implement disk quotas per user
- Restrict sudo commands
- Sandbox with namespaces/containers
- Audit of actions in real time

---

### 6. 🟠 Performance de Rede

**Issue**: Slow RDP connections on high latency networks.

**Impact**: Medium - Poor user experience

**Necessary Optimizations**:

```ini
# /etc/xrdp/xrdp.ini
[Globals]
tcp_nodelay=true
tcp_keepalive=true

# Compression
bitmap_compression=true
bulk_compression=true

# Codec
max_bpp=24
```

**Futuro**:
- Implement connection profiles (LAN, WAN, Mobile)
- Latency-based quality Auto-ajuste
- Support for RemoteFX

---

### 7. 🔴 Desktop Environments Installation Failures

**Problem**: DE installation may fail and leave the system inconsistent.

**Impact**: High - Unstable system

**Causas**:
- Unresolved dependencies
- Insufficient disk space
- Timeout during download
- Package conflicts

**Solutions**:

**Prevention**:
```python
def install_de_safe(self, de_id):
    # 1. Check disk space
    if not self.check_disk_space(de_id):
        return False, "Insufficient disk space"

    # 2. Simulate installation
    result = subprocess.run(['apt-get', 'install', '-s'] + packages)
    if result.returncode != 0:
        return False, "Dependency conflicts"

    # 3. Create restore point
    self.create_snapshot()

    # 4. Install with retry
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

**Problem**: Logs grow indefinitely.

**Impact**: Low - Excessive disk usage

**Solutions**:

**Auto Rotate**:
```python
# In logger.py - already implemented
RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

**Periodic Cleaning**:
```python
# Add to cron
@daily
find /var/log/rdp-session-manager/ -name "*.log.*" -mtime +30 -delete
```

---

### 9. 🔴 Backup and Recovery

**Problem**: There is no automatic backup of settings.

**Impact**: High - Data loss in case of failure

**Required Implementation**:

```python
# Daily automatic backup
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

**Problem**: System does not scale well for many users.

**Impact**: Medium - Growth limitation

**Current Limitations**:
- No clustering
- No load balancing
- Manual port management
- UI sincr

ona (crashes with many users)

**Future Solutions**:

1. **Async UI**:
```python
async def load_users(self):
    users = await self.user_manager.list_users_async()
    # Update UI
```

2. **Clustering**:
- Implement distributed backend
- Load balancing between servers
- Settings synchronization

3. **Database**:
- Migrate files to PostgreSQL/SQLite
- Cache with Redis
- REST API for multiple frontends

---

## Matriz de Prioridades

| Problem | Impact | Effort | Priority |
|----------|---------|---------|------------|
| Port Conflicts | High | Bass | **P0 - Critical** |
| Multiple Sessions (RAM) | High | Medium | **P0 - Critical** |
| Automatic Backup | High | Bass | **P1 - High** |
| Isolation Security | Medium | High | **P1 - High** |
| DE Installation | High | Medium | **P1 - High** |
| Permissions Home Dir | Medium | Bass | **P2 - Medium** |
| Compat. DEs | Medium | Medium | **P2 - Medium** |
| Performance Network | Medium | High | **P2 - Medium** |
| Logs Crescentes | Baixo | Baixo | **P3 - Baixo** |
| Scalability | Medium | High | **P3 - Long Term** |

## Improvement Checklist

### Curto Prazo (1-2 semanas)
- [ ] Implement RDP port pool
- [ ] Add disk space check
- [ ] Create initial setup script
- [ ] Implement automatic backup
- [ ] Add resource limits with cgroups

### Medium Term (1-2 months)
- [ ] Disk quota system
- [ ] Profile AppArmor restritivo
- [ ] RDP performance optimizations
- [ ] Retry logic for installing DEs
- [ ] Async UI for better responsiveness

### Longo Prazo (3-6 meses)
- [ ] Backend with database
- [ ] API REST
- [ ] Interface Web
- [ ] Suporte a clustering
- [ ] Integration with LDAP/AD

## How to Report Problems

1. **Check** if the issue is already listed
2. **Colete** logs relevantes:
   ```bash
   journalctl -u xrdp > xrdp.log
   cat ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log > app.log
   ```
3. **Open an issue** on GitHub with:
   - Description of the problem
   - Steps to reproduce
   - Logs anexados
   - System and application version

## Contributing to Solutions

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
