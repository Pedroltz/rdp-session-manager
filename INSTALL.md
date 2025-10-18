# Guia de Instalação Rápida

## 🚀 Instalação em 3 Passos

### Passo 1: Instalar Dependências

#### Debian/Ubuntu:
```bash
sudo apt update
sudo apt install -y \
    python3 \
    python3-gi \
    python3-psutil \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    xrdp
```

#### Fedora:
```bash
sudo dnf install -y \
    python3 \
    python3-gobject \
    python3-psutil \
    gtk4 \
    libadwaita \
    xrdp
```

### Passo 2: Criar Grupo RDP

```bash
sudo groupadd rdp-users
sudo mkdir -p /opt/rdp-users
sudo chmod 755 /opt/rdp-users
```

### Passo 3: Executar Aplicação

```bash
# Método mais simples
./run.sh

# Ou diretamente
python3 src/main.py
```

---

## 📋 Verificar Instalação

### Testar GTK4:
```bash
python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK4 OK')"
```

### Testar libadwaita:
```bash
python3 -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; print('Adwaita OK')"
```

### Testar psutil:
```bash
python3 -c "import psutil; print('psutil OK')"
```

---

## 🔧 Configuração Avançada

### Instalar PolicyKit Policy

```bash
sudo cp data/com.rdp.SessionManager.policy /usr/share/polkit-1/actions/
sudo chmod 644 /usr/share/polkit-1/actions/com.rdp.SessionManager.policy
```

### Instalar Helper Script

```bash
sudo cp scripts/rdp-session-helper.py /usr/libexec/
sudo chmod 755 /usr/libexec/rdp-session-helper.py
```

### Configurar xrdp

```bash
sudo systemctl enable xrdp
sudo systemctl start xrdp
```

---

## 🐛 Solução de Problemas

### Erro: "Namespace Adw not available"

**Solução:**
```bash
sudo apt install gir1.2-adw-1
```

### Erro: "No module named 'psutil'"

**Solução:**
```bash
sudo apt install python3-psutil
```

### Erro: "Grupo rdp-users não existe"

**Solução:**
```bash
sudo groupadd rdp-users
```

### Warnings do GTK sobre labels

**Causa:** Restrições de tamanho em alguns widgets
**Impacto:** Apenas visual, não afeta funcionalidade
**Ação:** Pode ser ignorado

---

## 📦 Instalação via Meson (Opcional)

Para instalação no sistema:

```bash
# Configurar build
meson setup builddir --prefix=/usr

# Compilar
meson compile -C builddir

# Instalar (requer sudo)
sudo meson install -C builddir

# Executar aplicação instalada
rdp-session-manager
```

---

## ✅ Checklist Pós-Instalação

- [ ] GTK4 instalado e funcionando
- [ ] libadwaita instalado e funcionando
- [ ] psutil instalado
- [ ] xrdp instalado e rodando
- [ ] Grupo `rdp-users` criado
- [ ] Diretório `/opt/rdp-users` criado
- [ ] PolicyKit policy instalada (opcional)
- [ ] Aplicação executa sem erros

---

## 🎯 Primeira Execução

Ao executar pela primeira vez, você verá:

1. **Janela Principal** - Vazia (nenhum usuário criado ainda)
2. **Informações do Servidor** - IP e status
3. **Botão "+"** - Para criar novo usuário

### Criar Primeiro Usuário:

1. Clique no botão **+** no canto superior esquerdo
2. Preencha:
   - Nome de usuário (ex: `testuser`)
   - Nome completo (ex: `Test User`)
   - Senha (mínimo 8 caracteres, com maiúsculas/minúsculas/números)
   - Confirmar senha
3. Escolha ambiente desktop (recomendado: **XFCE**)
4. Clique em **Criar**

⚠️ **Nota:** A criação de usuário requer privilégios administrativos via PolicyKit.

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique logs: `~/.local/share/rdp-session-manager/logs/`
2. Consulte: `docs/PROBLEMS_AND_SOLUTIONS.md`
3. Abra issue no GitHub

---

## 🎓 Próximos Passos

Após instalação bem-sucedida:

1. Leia o [README.md](README.md) para documentação completa
2. Consulte [DEVELOPMENT.md](docs/DEVELOPMENT.md) para desenvolvimento
3. Veja [CHANGELOG.md](CHANGELOG.md) para notas da versão
