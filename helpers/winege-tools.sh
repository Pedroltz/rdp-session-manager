#!/bin/bash
set -e

COMMAND="$1"
USERNAME="$2"

[ -z "$COMMAND" ] || [ -z "$USERNAME" ] && {
    echo "Uso: $0 {list-exes|view-logs|copy-files} USERNAME"
    echo ""
    echo "Comandos:"
    echo "  list-exes   - Listar executaveis disponiveis"
    echo "  view-logs   - Ver logs de execucao do Wine"
    echo "  copy-files  - Copiar arquivos do app para home"
    exit 1
}

HOME_DIR="/opt/rdp-users/$USERNAME"
[ ! -d "$HOME_DIR" ] && {
    echo "Erro: Usuario nao existe: $USERNAME"
    exit 1
}

find_installed_apps() {
    find "$HOME_DIR/.wine/drive_c/Program Files" "$HOME_DIR/.wine/drive_c/Program Files (x86)" \
        -name "*.exe" -type f 2>/dev/null | \
        grep -v -i "unins\|uninst\|windows nt\|internet explorer\|windows media\|windows mail\|windows photo\|wordpad\|notepad"
}

case "$COMMAND" in
    list-exes)
        echo "Executaveis para $USERNAME:"
        echo ""

        [ -d "$HOME_DIR/WindowsApps" ] && {
            echo "WindowsApps (portateis):"
            find "$HOME_DIR/WindowsApps" -name "*.exe" -type f 2>/dev/null | sed 's/^/  /'
            echo ""
        }

        [ -d "$HOME_DIR/.wine/drive_c" ] && {
            echo "Aplicativos instalados:"
            find_installed_apps | sed 's/^/  /'
            echo ""
        }

        echo "Executavel atual:"
        [ -f "$HOME_DIR/.winege_app_path" ] && cat "$HOME_DIR/.winege_app_path" || echo "  (nenhum)"
        ;;

    view-logs)
        LOG_FILE="$HOME_DIR/.winege_launch.log"
        [ ! -f "$LOG_FILE" ] && {
            echo "Nenhum log encontrado"
            exit 1
        }
        echo "=== Logs WineGE: $USERNAME ==="
        tail -100 "$LOG_FILE"
        ;;

    copy-files)
        [ ! -d "$HOME_DIR/.wine" ] && {
            echo "Erro: Wine Prefix nao encontrado"
            exit 1
        }

        INSTALLED_APP=$(find_installed_apps | head -n 1)
        [ -z "$INSTALLED_APP" ] && {
            echo "Erro: Nenhum aplicativo instalado"
            exit 1
        }

        APP_DIR=$(dirname "$INSTALLED_APP")
        echo "Copiando arquivos de: $(basename "$APP_DIR")"

        FILE_COUNT=0
        for EXT in ini dll dat png cfg xml conf jpg bmp ico; do
            while IFS= read -r -d '' file; do
                cp "$file" "$HOME_DIR/" 2>/dev/null && {
                    chown "$USERNAME:rdp-users" "$HOME_DIR/$(basename "$file")"
                    FILE_COUNT=$((FILE_COUNT + 1))
                }
            done < <(find "$APP_DIR" -maxdepth 1 -name "*.$EXT" -type f -print0 2>/dev/null)
        done

        echo "OK $FILE_COUNT arquivos copiados"
        ;;

    *)
        echo "Comando invalido: $COMMAND"
        exit 1
        ;;
esac

exit 0
