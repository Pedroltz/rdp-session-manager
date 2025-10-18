#!/bin/bash
# Script de inicialização do RDP Session Manager

echo "Iniciando RDP Session Manager..."

# Verificar dependências
if ! python3 -c "import gi" 2>/dev/null; then
    echo "Erro: PyGObject não encontrado"
    echo "Instale com: sudo apt install python3-gi"
    exit 1
fi

if ! python3 -c "import psutil" 2>/dev/null; then
    echo "Aviso: psutil não encontrado"
    echo "Instale com: sudo apt install python3-psutil"
fi

# Executar aplicação
python3 src/main.py
