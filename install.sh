#!/bin/bash
# Script de instalação do RDP Session Manager
# Compatível com Ubuntu, Debian e WSL

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para exibir mensagens
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Função para verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Função para verificar se está no WSL
is_wsl() {
    if grep -qEi "(Microsoft|WSL)" /proc/version &> /dev/null ; then
        return 0
    else
        return 1
    fi
}

# Verificar se está rodando como root
if [ "$EUID" -eq 0 ]; then
    error "NÃO execute este script como root (sudo)"
    error "O script pedirá senha quando necessário"
    exit 1
fi

# Verificar distribuição
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    error "Não foi possível detectar a distribuição"
    exit 1
fi

info "Sistema detectado: $OS $VER"

# Verificar se é WSL
if is_wsl; then
    warning "WSL detectado"
    warning "Note que algumas funcionalidades RDP podem ter limitações no WSL"
fi

# Verificar compatibilidade
case "$OS" in
    *"Ubuntu"*|*"Debian"*)
        success "Sistema compatível detectado"
        ;;
    *)
        warning "Sistema não testado: $OS"
        read -p "Deseja continuar mesmo assim? (s/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
        ;;
esac

echo ""
info "========================================="
info "  RDP Session Manager - Instalação"
info "========================================="
echo ""

# Atualizar lista de pacotes
info "Atualizando lista de pacotes..."
sudo apt-get update

# Instalar dependências do sistema
info "Instalando dependências do sistema..."

# Lista de pacotes essenciais
SYSTEM_PACKAGES=(
    # Python e pip
    python3
    python3-pip
    python3-venv
    python3-dev

    # GTK4 e libadwaita
    libgtk-4-1
    libgtk-4-dev
    libadwaita-1-0
    libadwaita-1-dev
    gir1.2-gtk-4.0
    gir1.2-adw-1

    # GObject Introspection
    libgirepository1.0-dev
    python3-gi
    python3-gi-cairo
    gir1.2-glib-2.0

    # Cairo
    libcairo2-dev
    pkg-config

    # PolicyKit (para elevação de privilégios)
    policykit-1

    # Ferramentas de sistema
    build-essential
    git
)

# Pacotes opcionais (RDP)
OPTIONAL_PACKAGES=(
    # Servidor RDP
    xrdp
    xorgxrdp

    # Cliente RDP
    freerdp2-x11

    # X11
    xorg
    x11-xserver-utils
)

info "Instalando pacotes essenciais..."
for package in "${SYSTEM_PACKAGES[@]}"; do
    if dpkg -l | grep -q "^ii  $package "; then
        success "$package já instalado"
    else
        info "Instalando $package..."
        sudo apt-get install -y "$package" || warning "Falha ao instalar $package (continuando...)"
    fi
done

echo ""
read -p "Deseja instalar pacotes opcionais RDP (xrdp, freerdp)? (S/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    info "Instalando pacotes opcionais..."
    for package in "${OPTIONAL_PACKAGES[@]}"; do
        if dpkg -l | grep -q "^ii  $package "; then
            success "$package já instalado"
        else
            info "Instalando $package..."
            sudo apt-get install -y "$package" || warning "Falha ao instalar $package (continuando...)"
        fi
    done
fi

# Criar diretório virtual environment (opcional)
echo ""
read -p "Deseja criar um ambiente virtual Python? (S/n) " -n 1 -r
echo
USE_VENV=false
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    USE_VENV=true
    info "Criando ambiente virtual..."
    python3 -m venv venv
    source venv/bin/activate
    success "Ambiente virtual criado e ativado"
fi

# Atualizar pip
info "Atualizando pip..."
python3 -m pip install --upgrade pip

# Instalar dependências Python
info "Instalando dependências Python..."
python3 -m pip install -r requirements.txt

success "Dependências instaladas com sucesso!"

# Tornar helpers executáveis
info "Configurando permissões dos scripts helper..."
chmod +x helpers/*.sh 2>/dev/null || warning "Diretório helpers/ não encontrado"

# Verificar instalação do xrdp
echo ""
if command_exists xrdp; then
    success "xrdp instalado"

    # Verificar se serviço está rodando
    if systemctl is-active --quiet xrdp 2>/dev/null; then
        success "Serviço xrdp está ativo"
    else
        warning "Serviço xrdp não está ativo"
        if ! is_wsl; then
            read -p "Deseja iniciar o serviço xrdp agora? (S/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                sudo systemctl enable xrdp
                sudo systemctl start xrdp
                success "Serviço xrdp iniciado"
            fi
        else
            warning "No WSL, você precisará iniciar o xrdp manualmente: sudo service xrdp start"
        fi
    fi
else
    warning "xrdp não instalado - O aplicativo não funcionará completamente sem ele"
fi

# Instruções finais
echo ""
info "========================================="
info "  Instalação Concluída!"
info "========================================="
echo ""

if [ "$USE_VENV" = true ]; then
    info "Para executar o aplicativo:"
    echo "  1. Ative o ambiente virtual: source venv/bin/activate"
    echo "  2. Execute: python3 src/main.py"
else
    info "Para executar o aplicativo:"
    echo "  python3 src/main.py"
fi

echo ""
info "Comandos úteis:"
echo "  - Verificar status xrdp: systemctl status xrdp"
if is_wsl; then
    echo "  - Iniciar xrdp (WSL): sudo service xrdp start"
else
    echo "  - Iniciar xrdp: sudo systemctl start xrdp"
fi
echo "  - Ver logs: tail -f ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log"

echo ""
success "Instalação finalizada com sucesso!"

exit 0
