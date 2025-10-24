# Correção: Bug de Detecção de Privilégios Sudo

## Problema Identificado

Quando um usuário recebia privilégios sudo e depois os tinha revogados, a interface continuava mostrando que o usuário ainda tinha privilégios sudo.

## Causa Raiz

O problema tinha duas origens:

### 1. Detecção Incorreta no Python

O método `is_superuser()` usava:
```python
sudo_group = grp.getgrnam('sudo')
return username in sudo_group.gr_mem
```

**Problema:** `grp.getgrnam().gr_mem` pode não refletir mudanças dinâmicas de grupo e pode não incluir todos os membros corretamente em todos os casos.

### 2. Remoção Incompleta do Grupo

O script helper usava:
```bash
/usr/sbin/deluser "$USERNAME" sudo 2>/dev/null || true
```

**Problema:** O comando `deluser` pode falhar silenciosamente em alguns casos sem remover o usuário do grupo corretamente.

## Solução Implementada

### 1. Detecção Melhorada (Python)

Agora usamos o comando `id -nG` que retorna **todos** os grupos do usuário de forma confiável:

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
- ✅ Retorna status em tempo real
- ✅ Inclui todos os grupos (primário + secundários)
- ✅ Funciona independente de cache
- ✅ Método padrão do sistema

### 2. Remoção Robusta (Shell Script)

Agora usamos `gpasswd -d` com fallback para `deluser`:

```bash
if /usr/bin/gpasswd -d "$USERNAME" sudo 2>/dev/null; then
    echo "✓ Privilégios revogados"
else
    # Fallback para deluser
    /usr/sbin/deluser "$USERNAME" sudo 2>/dev/null
fi
```

**Vantagens:**
- ✅ `gpasswd` é mais confiável para remover usuários de grupos
- ✅ Fallback garante compatibilidade
- ✅ Feedback claro sobre o resultado

## Como Testar

### 1. Criar um Usuário de Teste

```bash
# Via CLI
./rdpsm user create testuser -p "senha123" -d xfce

# Via GUI
Clique em "+" → Preencha formulário → "Criar"
```

### 2. Conceder Privilégios Sudo

```bash
# Via CLI
./rdpsm user sudo grant testuser

# Via GUI
Clique em "..." ao lado do usuário → Toggle "Superusuário" ON
```

### 3. Verificar Status (deve mostrar com sudo)

```bash
# CLI - Lista em JSON
./rdpsm user list --format json | grep -A 10 testuser

# Comando direto do sistema
id -nG testuser | grep sudo && echo "TEM SUDO" || echo "NÃO TEM SUDO"

# GUI - deve mostrar switch ativado
```

### 4. Revogar Privilégios Sudo

```bash
# Via CLI
./rdpsm user sudo revoke testuser

# Via GUI
Clique em "..." ao lado do usuário → Toggle "Superusuário" OFF
```

### 5. Verificar Status (deve mostrar sem sudo) ✅

```bash
# CLI - Lista em JSON
./rdpsm user list --format json | grep -A 10 testuser

# Comando direto do sistema
id -nG testuser | grep sudo && echo "TEM SUDO" || echo "NÃO TEM SUDO"

# GUI - deve mostrar switch desativado
```

## Script de Teste Automático

Você pode usar o script criado para testar:

```bash
/tmp/test-sudo-check.sh testuser
```

Saída esperada:
```
=== Verificação de Privilégios Sudo para testuser ===

1. Método id -nG (RECOMENDADO):
   ✗ Não tem sudo
   Grupos: testuser rdp-users

2. Método getent group sudo:
   ✗ Não tem sudo
   Membros do grupo sudo: trix,outrouser

3. Método groups command:
   ✗ Não tem sudo
   Grupos: testuser : testuser rdp-users
```

## Verificação Manual Adicional

Se ainda houver dúvidas, verifique diretamente:

```bash
# 1. Ver todos os grupos do usuário
id testuser

# 2. Ver membros do grupo sudo
getent group sudo

# 3. Tentar usar sudo (conecte via RDP primeiro)
# Conecte como testuser via RDP e execute:
sudo whoami
# Se sem privilégios, deve dar erro "user is not in the sudoers file"
```

## Arquivos Modificados

1. **`src/core/user_manager.py`** - Método `is_superuser()` melhorado
2. **`helpers/toggle-user-sudo.sh`** - Script de revogação melhorado
3. **`CHANGELOG.md`** - Documentação da correção

## Resultado Esperado

✅ **Antes da correção:** Usuário mantinha sudo mesmo após revogação na interface
✅ **Depois da correção:** Privilégios refletem imediatamente após revogação

---

**Data da Correção:** 2025-10-23
**Versão:** 0.2.1
**Status:** ✅ CORRIGIDO
