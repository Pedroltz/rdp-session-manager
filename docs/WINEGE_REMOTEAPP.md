# WineGE RemoteApp - Guia de Uso

Este documento explica como criar RemoteApps que executam aplicativos Windows usando **WineGE** (Wine-GE Custom) no RDP Session Manager.

## O que é WineGE RemoteApp?

WineGE RemoteApp permite que você execute aplicativos Windows (.exe) como RemoteApps via RDP, usando o Wine-GE (uma versão melhorada do Wine mantida por GloriousEggroll) em vez do Wine convencional.

### Por que WineGE em vez de Wine?

- **Melhor compatibilidade** com jogos e aplicativos modernos
- **Patches adicionais** para DirectX, DXVK, VKD3D
- **Performance superior** em muitos casos
- **Suporte a tecnologias recentes** (FSR, Ray Tracing via VKD3D, etc.)
- **Atualizações frequentes** com correções de bugs

## Requisitos

- Aplicativo Windows (.exe) - pode ser:
  - Instalador (setup.exe, installer.exe)
  - Executável portátil (app.exe)
- Espaço em disco suficiente (~2-3GB para WineGE + aplicativo)
- Conexão com internet (para download do WineGE na primeira vez)

## Como Criar um Usuário WineGE RemoteApp

### Via Interface Gráfica (GUI)

1. Abra o RDP Session Manager
2. Clique em "Add User"
3. Preencha os dados do usuário
4. Em "Session Type", selecione **"WineGE RemoteApp"**
5. Em "Application Command", clique em "Browse" e selecione o arquivo .exe
6. (Opcional) Adicione argumentos em "Application Arguments"
7. Clique em "Create User"

O sistema irá:
- Criar o usuário
- Baixar e instalar o WineGE (~1.5GB)
- Criar um Wine Prefix
- Instalar o aplicativo (se for um instalador)
- Configurar o RemoteApp

### Via Linha de Comando (CLI)

#### Criar novo usuário com WineGE RemoteApp:

```bash
# Exemplo com aplicativo portátil
rdpsm user create winuser1 \
    --session-type winege-remoteapp \
    --app-command /path/to/MyApp.exe \
    --fullname "Windows App User"

# Exemplo com instalador
rdpsm user create winuser2 \
    --session-type winege-remoteapp \
    --app-command /path/to/MyAppSetup.exe \
    --fullname "Windows Game User"

# Com argumentos
rdpsm user create winuser3 \
    --session-type winege-remoteapp \
    --app-command /path/to/MyApp.exe \
    --app-args "--windowed --no-intro" \
    --fullname "Windows App User"
```

## Adicionar WineGE App a Usuário Existente

Se você já tem um usuário criado e quer convertê-lo para WineGE RemoteApp:

### Via CLI:

```bash
# 1. Configurar WineGE no usuário (como root ou com pkexec)
sudo /usr/local/lib/rdp-session-manager/helpers/setup-winege-app.sh \
    USERNAME \
    /opt/rdp-users/USERNAME \
    /path/to/app.exe

# 2. Alterar tipo de sessão do usuário
rdpsm user session-type USERNAME winege-remoteapp
```

## Estrutura de Arquivos

Após a configuração, o usuário WineGE terá a seguinte estrutura:

```
/opt/rdp-users/USERNAME/
├── .wine/                          # Wine Prefix (ambiente Windows virtualizado)
│   ├── drive_c/                    # Disco C: virtual
│   │   ├── Program Files/          # Aplicativos instalados
│   │   ├── Program Files (x86)/
│   │   └── users/                  # Dados do usuário Windows
│   └── ...
├── .local/share/winege/            # Instalação do WineGE
│   └── wine-ge-custom-GE-Proton9-20/
├── WindowsApps/                    # Executáveis copiados
│   └── MyApp.exe
├── .winege_app_path                # Caminho do executável principal
├── .winege_config                  # Configuração do WineGE
├── .launch_winege_app.sh           # Script wrapper de lançamento
└── .xsession                       # Script de inicialização RDP
```

## Exemplos de Uso

### Exemplo 1: Notepad++ (Aplicativo Portátil)

```bash
# Baixar Notepad++ portátil primeiro
wget https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.6/npp.8.6.portable.x64.zip
unzip npp.8.6.portable.x64.zip -d /tmp/notepadpp

# Criar usuário
rdpsm user create notepad_user \
    --session-type winege-remoteapp \
    --app-command /tmp/notepadpp/notepad++.exe \
    --fullname "Notepad++ User"
```

### Exemplo 2: Aplicativo com Instalador

```bash
# Supondo que você tem um instalador MyAppSetup.exe
rdpsm user create myapp_user \
    --session-type winege-remoteapp \
    --app-command /home/user/Downloads/MyAppSetup.exe \
    --fullname "My App User"

# Durante a criação, o instalador será executado interativamente
# Siga as instruções do instalador Windows
```

### Exemplo 3: Jogo Steam (exemplo avançado)

```bash
# Para jogos, você pode precisar de argumentos especiais
rdpsm user create game_user \
    --session-type winege-remoteapp \
    --app-command /path/to/game.exe \
    --app-args "-windowed -high" \
    --fullname "Game User"
```

## Troubleshooting

### Aplicativo não inicia

1. Verifique os logs:
   ```bash
   rdpsm user info USERNAME
   journalctl -xe | grep xrdp
   ```

2. Teste manualmente:
   ```bash
   su - USERNAME
   bash ~/.launch_winege_app.sh
   ```

### Instalador não encontrou o executável

Após a instalação, o sistema tenta encontrar automaticamente o .exe principal. Se falhar:

1. Encontre o executável manualmente:
   ```bash
   find /opt/rdp-users/USERNAME/.wine/drive_c/ -name "*.exe" | grep -v unins
   ```

2. Atualize o caminho:
   ```bash
   echo "/path/to/correct/app.exe" | sudo tee /opt/rdp-users/USERNAME/.winege_app_path
   ```

### WineGE não baixa

- Verifique conexão com internet
- Baixe manualmente de: https://github.com/GloriousEggroll/wine-ge-custom/releases
- Extraia em `/opt/rdp-users/USERNAME/.local/share/winege/`

### Aplicativo precisa de bibliotecas adicionais

Entre no Wine Prefix do usuário e instale:

```bash
su - USERNAME
export WINEPREFIX="$HOME/.wine"
export PATH="$HOME/.local/share/winege/wine-ge-custom-GE-Proton9-20/bin:$PATH"

# Instalar dependências via winetricks
winetricks vcrun2019 dotnet48
```

## Limitações

- **Jogos com anti-cheat**: Podem não funcionar
- **DirectX 12**: Suporte limitado via VKD3D
- **Aplicativos que requerem drivers**: Podem ter problemas
- **Performance**: Depende do hardware e compatibilidade do aplicativo

## Dicas de Performance

1. **Use SSD**: WineGE funciona melhor com armazenamento rápido
2. **RAM suficiente**: Recomendado 4GB+ por usuário
3. **GPU dedicada**: Para jogos ou apps gráficos
4. **Vulkan drivers**: Instale drivers Vulkan atualizados

## Comparação: RemoteApp vs WineGE RemoteApp

| Característica | RemoteApp | WineGE RemoteApp |
|----------------|-----------|------------------|
| Tipo de App | Linux nativo | Windows (.exe) |
| Instalação | Rápida | Lenta (download WineGE) |
| Espaço em disco | Pequeno | ~2-3GB |
| Performance | Nativa | Emulada (pode ser mais lenta) |
| Compatibilidade | 100% Linux | Varia por app |

## Referências

- [WineGE GitHub](https://github.com/GloriousEggroll/wine-ge-custom)
- [Wine AppDB](https://appdb.winehq.org/) - Compatibilidade de aplicativos
- [ProtonDB](https://www.protondb.com/) - Compatibilidade de jogos
- [Winetricks](https://github.com/Winetricks/winetricks)

## Suporte

Para problemas específicos com WineGE RemoteApps, abra uma issue em:
https://github.com/seu-usuario/rdp-session-manager/issues
