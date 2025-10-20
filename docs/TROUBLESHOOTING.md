# Troubleshooting Guide

## Common Issues and Solutions

This document provides solutions to known issues and anticipates potential future problems with the RDP Session Manager.

---

## Critical Issues

### RDP Port Conflicts

**Symptom**: Multiple users attempting to use the same RDP port

**Impact**: High - Prevents creation of new users

**Possible Causes**:
- System not properly checking ports in use
- Conflicting manual port configuration
- Legacy xrdp processes still occupying ports

**Solutions**:

**Short Term**:
```python
# Implement robust verification in rdp_config.py
def is_port_available(self, port: int) -> bool:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False
```

**Long Term**:
- Implement managed port pool
- Add configurable RDP port range
- Create dynamic allocation system

---

### Memory Management with Multiple Sessions

**Symptom**: Server becomes slow with many active RDP sessions

**Impact**: High - Degraded performance

**Causes**:
- Each DE consumes 500MB-2GB of RAM
- Processes not properly terminated on disconnect
- No resource limits per session

**Solutions**:

**Immediate**:
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

**Future**:
- Implement cgroups for each session
- Auto-kill inactive sessions
- Resource usage dashboard
- Resource limit alerts

---

## Medium Priority Issues

### Custom Home Directory Permissions

**Symptom**: Creating RDP users in `/opt/rdp-users` fails due to permissions

**Impact**: Medium - Users cannot be created

**Possible Causes**:
- Directory `/opt/rdp-users` does not exist
- Incorrect permissions on parent directory
- SELinux/AppArmor blocking access

**Solutions**:

**Immediate**:
```bash
# Initial setup script
sudo mkdir -p /opt/rdp-users
sudo chmod 755 /opt/rdp-users
sudo chown root:rdp-users /opt/rdp-users
```

**Future**:
- Automatically verify and create directory on first use
- Add permission check on startup
- Support alternative configurable directories

---

### Desktop Environment Compatibility

**Symptom**: Some DEs do not work well via RDP

**Impact**: Medium - Poor user experience

**Problematic DEs**:
- **GNOME**: Wayland does not work via RDP (requires X11)
- **KDE Plasma**: May have performance issues
- **Cinnamon**: Visual effects cause lag

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

**Recommendation**: Use XFCE or MATE for best RDP experience.

---

### Desktop Environment Installation Failures

**Symptom**: DE installation may fail leaving system inconsistent

**Impact**: High - Unstable system

**Causes**:
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

    # 5. Rollback if failed
    self.restore_snapshot()
    return False, "Installation failed"
```

---

## Lower Priority Issues

### Network Performance

**Symptom**: Slow RDP connections on high-latency networks

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

**Future**:
- Implement connection profiles (LAN, WAN, Mobile)
- Auto-adjust quality based on latency
- RemoteFX support

---

### RDP User Security Isolation

**Symptom**: RDP users can access system resources

**Impact**: Medium - Security risk

**Risks**:
- Access to system files
- Installation of unauthorized software
- Excessive resource consumption

**Solutions**:

**Immediate**:
```bash
# Create restrictive AppArmor profile
sudo aa-genprof /bin/bash
# Configure in "complain" mode initially
```

**Long Term**:
- Implement disk quotas per user
- Restrict sudo commands
- Sandbox with namespaces/containers
- Real-time action auditing

---

### Log Growth

**Symptom**: Logs grow indefinitely

**Impact**: Low - Excessive disk usage

**Solutions**:

**Automatic Rotation**:
```python
# In logger.py - already implemented
RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

**Periodic Cleanup**:
```python
# Add to cron
@daily
find /var/log/rdp-session-manager/ -name "*.log.*" -mtime +30 -delete
```

---

### Backup and Recovery

**Symptom**: No automatic configuration backup

**Impact**: High - Data loss in case of failure

**Required Implementation**:

```python
# Automatic daily backup
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

### Scalability

**Symptom**: System does not scale well for many users

**Impact**: Medium - Growth limitation

**Current Limitations**:
- No clustering
- No load balancing
- Manual port management
- Synchronous UI (freezes with many users)

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
- Configuration synchronization

3. **Database**:
- Migrate from files to PostgreSQL/SQLite
- Cache with Redis
- REST API for multiple frontends

---

## Priority Matrix

| Problem | Impact | Effort | Priority |
|---------|---------|---------|----------|
| Port Conflicts | High | Low | **P0 - Critical** |
| Multiple Sessions (RAM) | High | Medium | **P0 - Critical** |
| Automatic Backup | High | Low | **P1 - High** |
| Security Isolation | Medium | High | **P1 - High** |
| DE Installation | High | Medium | **P1 - High** |
| Home Dir Permissions | Medium | Low | **P2 - Medium** |
| DE Compatibility | Medium | Medium | **P2 - Medium** |
| Network Performance | Medium | High | **P2 - Medium** |
| Growing Logs | Low | Low | **P3 - Low** |
| Scalability | Medium | High | **P3 - Long Term** |

---

## Improvement Checklist

### Short Term (1-2 weeks)
- [ ] Implement RDP port pool
- [ ] Add disk space verification
- [ ] Create initial setup script
- [ ] Implement automatic backup
- [ ] Add resource limits with cgroups

### Medium Term (1-2 months)
- [ ] Disk quota system
- [ ] Restrictive AppArmor profile
- [ ] RDP performance optimizations
- [ ] Retry logic for DE installation
- [ ] Async UI for better responsiveness

### Long Term (3-6 months)
- [ ] Database backend
- [ ] REST API
- [ ] Web interface
- [ ] Clustering support
- [ ] LDAP/AD integration

---

## How to Report Issues

1. **Verify** if the problem is already listed
2. **Collect** relevant logs:
   ```bash
   journalctl -u xrdp > xrdp.log
   cat ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log > app.log
   ```
3. **Open Issue** on GitHub with:
   - Problem description
   - Steps to reproduce
   - Attached logs
   - System and application version

---

## Contributing Solutions

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

---

**Last Updated**: 2025-10-18
