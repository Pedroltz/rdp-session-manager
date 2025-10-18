# Instalação do RDP Session Manager

Guia de instalação para Ubuntu, Debian e WSL.

## Requisitos do Sistema

- **Ubuntu** 20.04 ou superior
- **Debian** 11 (Bullseye) ou superior
- **WSL** (Windows Subsystem for Linux) com Ubuntu/Debian
- Python 3.8 ou superior

## Instalação Rápida

### Script Automático (Recomendado)

```bash
# 1. Clone ou baixe o projeto
cd RemoteApps-RDP

# 2. Execute o script de instalação
./install.sh
```

O script irá:
- ✅ Detectar automaticamente seu sistema (Ubuntu/Debian/WSL)
- ✅ Instalar todas as dependências do sistema
- ✅ Instalar dependências Python
- ✅ Configurar permissões necessárias
- ✅ Opcionalmente instalar e configurar xrdp

## Executando o Aplicativo

```bash
# Com ambiente virtual
source venv/bin/activate
python3 src/main.py

# Sem ambiente virtual
python3 src/main.py
```

## Documentação Completa

Para instruções detalhadas de instalação manual, solução de problemas e configuração WSL, consulte o arquivo completo de instalação.
