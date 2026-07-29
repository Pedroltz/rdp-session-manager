# Fix: Sudo Privilege Detection Bug

## Problem Identified

When a user was granted sudo privileges and then had them revoked, the interface continued to show that the user still had sudo privileges.

## Causa Raiz

The problem had two root causes:

### 1. Incorrect Detection in Python

The `is_superuser()` method used:
```python
sudo_group = grp.getgrnam('sudo')
return username in sudo_group.gr_mem
```

**Issue:** `grp.getgrnam().gr_mem` may not reflect dynamic group changes and may not include all members correctly in all cases.

### 2. Incomplete Group Removal

O script helper usava:
```bash
/usr/sbin/deluser "$USERNAME" sudo 2>/dev/null || true
```

**Issue:** The `deluser` command may fail silently in some cases without correctly removing the user from the group.

## Implemented Solution

### 1. Improved Detection (Python)

Now we use the command `id -nG` which reliably returns **all** of the user's groups:

```python
def is_superuser(self, username: str) -> bool:
    result = subprocess.run(
        ['id', '-nG', username],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0:
        groups = result.stdout.strip().split()
        return 'sudo' in groups
```

**Vantagens:**
- ✅ Returns status in real time
- ✅ Includes all groups (primary + secondary)
- ✅ Funciona independente de cache
- ✅ System default method

### 2. Robust Removal (Shell Script)

Now we use `gpasswd -d` with fallback to `deluser`:

```bash
if /usr/bin/gpasswd -d "$USERNAME" sudo 2>/dev/null; then
    echo "✓ Privileges revoked"
else
    # Fallback to deluser
    /usr/sbin/deluser "$USERNAME" sudo 2>/dev/null
fi
```

**Vantagens:**
- ✅ `gpasswd` is more reliable for removing users from groups
- ✅ Fallback ensures compatibility
- ✅ Clear feedback on the result

## How to Test

### 1. Create a Test User

```bash
# Via CLI
./rdpsm user create testuser -p "senha123" -d xfce

# Via GUI
Click "+" → Fill form → "Create"
```

### 2. Grant Sudo Privileges

```bash
# Via CLI
./rdpsm user sudo grant testuser

# Via GUI
Click "..." next to the user → Toggle "Superuser" ON
```

### 3. Check Status (should show with sudo)

```bash
# CLI - List in JSON
./rdpsm user list --format json | grep -A 10 testuser

# Direct system command
id -nG testuser | grep sudo && echo "TEM SUDO" || echo "NO SUDO"

# GUI - should show switch enabled
```

### 4. Revoke Sudo Privileges

```bash
# Via CLI
./rdpsm user sudo revoke testuser

# Via GUI
Click "..." next to the user → Toggle "Superuser" OFF
```

### 5. Check Status (should show without sudo) ✅

```bash
# CLI - List in JSON
./rdpsm user list --format json | grep -A 10 testuser

# Direct system command
id -nG testuser | grep sudo && echo "TEM SUDO" || echo "NO SUDO"

# GUI - should show switch disabled
```

## Automatic Test Script

You can use the created script to test:

```bash
/tmp/test-sudo-check.sh testuser
```

Expected output:
```
=== Sudo Privilege Check for testuser ===

1. Method id -nG (RECOMMENDED):
   ✗ No sudo
   Groups: testuser rdp-users

2. getent group sudo method:
   ✗ No sudo
   sudo group members: trix,otheruser

3. groups command method:
   ✗ No sudo
   Groups: testuser : testuser rdp-users
```

## Additional Manual Verification

If you still have doubts, check directly:

```bash
#1. View all user groups
id testuser

# 2. View sudo group members
getent group sudo

# 3. Try using sudo (connect via RDP first)
# Connect as testuser via RDP and run:
sudo whoami
# If without privileges, it should give an error "user is not in the sudoers file"
```

## Modified Files

1. **`src/core/user_manager.py`** - Improved `is_superuser()` method
2. **`helpers/toggle-user-sudo.sh`** - Improved revocation script
3. **`CHANGELOG.md`** - Fix documentation

## Expected Result

✅ **Before the fix:** User kept sudo even after revoking it in the interface
✅ **After fix:** Privileges reflect immediately after revocation

---

**Correction Date:** 2025-10-23
**Version:** 0.2.1
**Status:** ✅ CORRECTED
