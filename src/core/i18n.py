#!/usr/bin/env python3
"""
Internationalization (i18n) Module for RDP Session Manager.

Detects the operating system language and provides translation lookups
for English (en), Portuguese (pt_BR/pt), and Spanish (es).
Allows easy addition of new languages via dictionary or register_language().
"""

from __future__ import annotations

import locale
import os
from typing import Dict, List, Optional


# Translation Catalogs
# English is the base language. Translations for Portuguese (pt_BR) and Spanish (es) are defined below.
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "pt_BR": {
        # General & Actions
        "RDP Session Manager": "RDP Session Manager",
        "General": "Geral",
        "Preferences": "Preferências",
        "About": "Sobre",
        "Language": "Idioma",
        "Select the interface language for the application": "Selecione o idioma da interface da aplicação",
        "Interface Language": "Idioma da Interface",
        "Auto (System default)": "Automático (Padrão do Sistema)",
        "Language changed. Please restart the application to update all screens.": "Idioma alterado. Reinicie a aplicação para atualizar todas as telas.",
        "Quit": "Sair",
        "Cancel": "Cancelar",
        "OK": "OK",
        "Close": "Fechar",
        "Create": "Criar",
        "Save": "Salvar",
        "Delete": "Excluir",
        "Edit": "Editar",
        "Refresh": "Atualizar",
        "Search": "Pesquisar",
        "Connect": "Conectar",
        "Connecting…": "Conectando…",
        "Configure": "Configurar",
        "Applying…": "Aplicando…",
        "Apply Changes": "Aplicar Alterações",
        "Try Again": "Tentar Novamente",
        "Copy Commands": "Copiar Comandos",
        "View Instructions": "Ver Instruções",
        "Copy IP Address": "Copiar Endereço IP",
        "No changes were made": "Nenhuma alteração foi feita",
        "Active": "Ativo",
        "Inactive": "Inativo",
        "Connected": "Conectado",
        "Disconnected": "Desconectado",

        # Main Window
        "Server Information": "Informações do Servidor",
        "IP Address": "Endereço IP",
        "Detecting…": "Detectando…",
        "Active Sessions": "Sessões Ativas",
        "0 sessions": "0 sessões",
        "{count} active sessions": "{count} sessões ativas",
        "Health & Diagnostics": "Saúde e Diagnósticos",
        "Health report is not ready yet": "O relatório de saúde ainda não está pronto",
        "Check system health now": "Verificar saúde do sistema agora",
        "Healthy · {count} checks passed": "Saudável · {count} verificações passaram",
        "{count} critical issue(s)": "{count} problema(s) crítico(s)",
        "{count} warning(s)": "{count} aviso(s)",
        "{count} check(s) unavailable": "{count} verificação(ões) indisponível(is)",
        "Search users...": "Buscar usuários...",
        "Create a new RDP user": "Criar novo usuário RDP",
        "No RDP Users": "Nenhum usuário RDP",
        "Add your first RDP user to start managing sessions": "Adicione seu primeiro usuário RDP para começar a gerenciar sessões",
        "New User": "Novo Usuário",
        "Users": "Usuários",
        "Delete User": "Excluir Usuário",
        "Are you sure you want to delete user \"{username}\"?": "Tem certeza que deseja excluir o usuário \"{username}\"?",
        "This action cannot be undone and will delete the user's home directory.": "Esta ação não pode ser desfeita e excluirá o diretório home do usuário.",
        "User {username} enabled": "Usuário {username} habilitado",
        "Error enabling user {username}": "Erro ao habilitar usuário {username}",
        "User {username} disabled": "Usuário {username} desabilitado",
        "Error disabling user {username}": "Erro ao desabilitar usuário {username}",
        "Error changing status of user {username}": "Erro ao alterar status do usuário {username}",
        "RDP password cannot be empty": "A senha RDP não pode estar vazia",
        "Passwords do not match": "As senhas não coincidem",
        "Repairing {username}; authenticate once...": "Reparando {username}; autentique uma vez...",
        "Sudo privileges granted—reconnect to apply": "Privilégios de sudo concedidos — reconecte para aplicar",
        "Error granting sudo privileges to {username}": "Erro ao conceder privilégios de sudo a {username}",
        "Sudo privileges revoked—reconnect to apply": "Privilégios de sudo revogados — reconecte para aplicar",
        "Error revoking sudo privileges from {username}": "Erro ao revogar privilégios de sudo de {username}",
        "Error changing sudo privileges for {username}": "Erro ao alterar privilégios de sudo de {username}",
        "Ending sessions for {username}...": "Encerrando sessões de {username}...",
        "Removing user {username}...": "Removendo usuário {username}...",
        "User {username} removed successfully": "Usuário {username} removido com sucesso",
        "Error removing user {username}": "Erro ao remover usuário {username}",
        "No executables found": "Nenhum executável encontrado",
        "Executable selected": "Executável selecionado",
        "Application command cannot be empty for RemoteApp": "O comando do aplicativo não pode estar vazio para RemoteApp",
        "Executable path cannot be empty for Windows RemoteApp": "O caminho do executável não pode estar vazio para Windows RemoteApp",
        "File not found: {path}": "Arquivo não encontrado: {path}",
        "Username cannot be empty": "O nome de usuário não pode estar vazio",
        "Password must be at least 6 characters long": "A senha deve ter pelo menos 6 caracteres",
        "Error changing full name": "Erro ao alterar nome completo",
        "Error changing password": "Erro ao alterar senha",
        "Error changing session type": "Erro ao alterar tipo de sessão",
        "Error changing application": "Erro ao alterar aplicativo",
        "Error updating WineGE executable": "Erro ao atualizar executável WineGE",
        "Error changing arguments": "Erro ao alterar argumentos",
        "Error renaming user": "Erro ao renomear usuário",
        "Settings saved: {changes}": "Configurações salvas: {changes}",
        "Error updating settings": "Erro ao atualizar configurações",
        "{connection_string} copied to clipboard": "{connection_string} copiado para a área de transferência",
        "Password cannot be empty": "A senha não pode estar vazia",
        "FreeRDP not found": "FreeRDP não encontrado",
        "Opening RemoteApp: {app_name}...": "Abrindo RemoteApp: {app_name}...",
        "Opening {cmd}...": "Abrindo {cmd}...",
        "Error opening FreeRDP: {error}": "Erro ao abrir FreeRDP: {error}",
        "IP {ip} copied to clipboard": "IP {ip} copiado para a área de transferência",

        # Preferences - General
        "RDP Server Port": "Porta do Servidor RDP",
        "Default port configuration for RDP client connections": "Configuração da porta padrão para conexões de clientes RDP",
        "Default Port": "Porta Padrão",
        "Port used by RDP users (default: 3389)": "Porta usada por usuários RDP (padrão: 3389)",

        # Preferences - Server & Capacity
        "Server & Capacity": "Servidor e Capacidade",
        "Session Allocation": "Alocação de Sessões",
        "Concurrent session limits and resource reservation": "Limites de sessões simultâneas e reserva de recursos",
        "Linux Session Slots": "Slots de Sessão Linux",
        "1,280 MB RAM per slot (linux-light)": "1.280 MB de RAM por slot (linux-light)",
        "Windows / Wine Session Slots": "Slots de Sessão Windows / Wine",
        "2,560 MB RAM per slot (windows-standard)": "2.560 MB de RAM por slot (windows-standard)",
        "Max Concurrent Sessions": "Máximo de Sessões Simultâneas",
        "Global ceiling for active RDP sessions": "Teto global para sessões RDP ativas",
        "Host Memory Reserve (%)": "Reserva de Memória do Sistema (%)",
        "RAM reserved for system OS operations": "RAM reservada para operações do sistema operacional",
        "Memory Safety Budget": "Orçamento Seguro de Memória",
        "Allocated Memory": "Memória Alocada",
        "Network Access Restriction": "Restrição de Acesso de Rede",
        "Restrict RDP access to a specific private network or VPN": "Restringir acesso RDP a uma rede privada ou VPN específica",
        "Allowed Network (CIDR)": "Rede Permitida (CIDR)",
        "Capacity Management": "Gerenciamento de Capacidade",
        "Auto-Detect Safe Capacity": "Auto-detectar Capacidade Segura",
        "Automatically compute safe slots based on host RAM": "Calcular slots seguros automaticamente com base na RAM do host",
        "Recommend": "Recomendar",
        "Apply Server Profile": "Aplicar Perfil do Servidor",
        "Save settings and update system resource limits": "Salvar configurações e atualizar limites de recursos do sistema",
        "✓ Safe Budget": "✓ Orçamento Seguro",
        "⚠ Exceeds RAM": "⚠ Excede a RAM",
        "Server profile applied successfully": "Perfil do servidor aplicado com sucesso",
        "Please enter an allowed network in CIDR format (e.g., 192.168.1.0/24)": "Preencha a rede permitida em formato CIDR (ex: 192.168.1.0/24)",
        "Invalid network format. Use CIDR notation like 192.168.1.0/24": "Formato de rede inválido. Use notação CIDR como 192.168.1.0/24",

        # User Dialog
        "Create New RDP User": "Criar Novo Usuário RDP",
        "Basic Information": "Informações Básicas",
        "Username": "Nome de Usuário",
        "Full Name": "Nome Completo",
        "Security": "Segurança",
        "Password": "Senha",
        "Confirm Password": "Confirmar Senha",
        "Session Type": "Tipo de Sessão",
        "Connection Mode": "Modo de Conexão",
        "Choose between a full desktop or a single application": "Escolha entre um desktop completo ou um único aplicativo",
        "Full Desktop": "Desktop Completo",
        "RemoteApp (Linux Application)": "RemoteApp (Aplicativo Linux)",
        "Windows RemoteApp (umu)": "Windows RemoteApp (umu)",
        "Desktop Environment": "Ambiente Gráfico",
        "Install Desktop Environment": "Instalar Ambiente Gráfico",
        "Automatically install if not present on the system": "Instalar automaticamente se não estiver presente no sistema",
        "Application": "Aplicativo",
        "Select Application": "Selecionar Aplicativo",
        "Custom Application Command": "Comando Personalizado do Aplicativo",
        "Application Arguments (Optional)": "Argumentos do Aplicativo (Opcional)",
        "Windows Executable (.exe)": "Executável Windows (.exe)",
        "Select .exe File": "Selecionar Arquivo .exe",
        "Executable Path": "Caminho do Executável",
        "Auto-start Application": "Iniciar Aplicativo Automaticamente",
        "Start application automatically on session connect": "Iniciar aplicativo automaticamente ao conectar a sessão",
        "User created successfully": "Usuário criado com sucesso",
        "Error creating user: {error}": "Erro ao criar usuário: {error}",
        "Creating user...": "Criando usuário...",
        "Installing Desktop Environment...": "Instalando Ambiente Gráfico...",

        # Health Dialog
        "System Health": "Saúde do Sistema",
        "All statuses": "Todos os status",
        "Healthy": "Saudável",
        "Warning": "Aviso",
        "Critical": "Crítico",
        "Unknown": "Desconhecido",
        "All components": "Todos os componentes",
        "Host": "Host",
        "User": "Usuário",
        "Session": "Sessão",
        "Windows runtime": "Ambiente Windows",
        "Search user, check, or evidence…": "Buscar usuário, verificação ou evidência…",
        "No checks match the selected filters.": "Nenhuma verificação corresponde aos filtros selecionados.",
        "Check": "Verificação",
        "Component": "Componente",
        "Status": "Status",
        "Evidence": "Evidência",
        "Remediation": "Correção",
        "Repair": "Reparar",
        "Fix": "Corrigir",
        "Running health check…": "Executando verificação de saúde…",

        # Connection Sources Dialog
        "Connection Sources": "Fontes de Conexão",
        "Manage connection profiles and sources for user": "Gerenciar perfis e fontes de conexão para o usuário",
        "Add Profile": "Adicionar Perfil",
        "Edit Profile": "Editar Perfil",
        "Delete Profile": "Excluir Perfil",
        "Profile Name": "Nome do Perfil",
        "Export .rdp File": "Exportar Arquivo .rdp",
        "Exported .rdp file successfully": "Arquivo .rdp exportado com sucesso",
        "Error exporting .rdp file": "Erro ao exportar arquivo .rdp",

        # Application / Installation Dialogs
        "xrdp Server Not Found": "Servidor xrdp Não Encontrado",
        "The xrdp server is required to create remote RDP sessions.\n\nWould you like to install it now?": "O servidor xrdp é necessário para criar sessões RDP remotas.\n\nDeseja instalá-lo agora?",
        "Install xrdp": "Instalar xrdp",
        "Installing xrdp": "Instalando xrdp",
        "Installing the RDP server...\nThis may take a few minutes.": "Instalando o servidor RDP...\nIsso pode levar alguns minutos.",
        "Preparing installation...": "Preparando instalação...",
        "Installation complete!": "Instalação concluída!",
        "Installation error": "Erro de instalação",
        "xrdp Installed Successfully": "xrdp Instalado com Sucesso!",
        "The xrdp server was installed and configured successfully.\n\nYou can now create RDP users!": "O servidor xrdp foi instalado e configurado com sucesso.\n\nAgora você pode criar usuários RDP!",
        "xrdp Installation Error": "Erro de Instalação do xrdp",
        "Manual xrdp Installation": "Instalação Manual do xrdp",
        "Commands copied to the clipboard!": "Comandos copiados para a área de transferência!",
        "Installing FreeRDP": "Instalando FreeRDP",
        "Installing the RDP client...\nThis may take a few minutes.": "Instalando o cliente RDP...\nIsso pode levar alguns minutos.",
        "FreeRDP Installed Successfully": "FreeRDP Instalado com Sucesso!",
        "The FreeRDP client was installed successfully.\n\nYou can now connect to your RDP users!": "O cliente FreeRDP foi instalado com sucesso.\n\nAgora você pode se conectar aos seus usuários RDP!",
        "FreeRDP Installation Error": "Erro de Instalação do FreeRDP",
    },
    "es": {
        # General & Actions
        "RDP Session Manager": "RDP Session Manager",
        "General": "General",
        "Preferences": "Preferencias",
        "About": "Acerca de",
        "Language": "Idioma",
        "Select the interface language for the application": "Seleccione el idioma de la interfaz para la aplicación",
        "Interface Language": "Idioma de la Interfaz",
        "Auto (System default)": "Automático (Predeterminado del Sistema)",
        "Language changed. Please restart the application to update all screens.": "Idioma cambiado. Reinicie la aplicación para actualizar todas las pantallas.",
        "Quit": "Salir",
        "Cancel": "Cancelar",
        "OK": "OK",
        "Close": "Cerrar",
        "Create": "Crear",
        "Save": "Guardar",
        "Delete": "Eliminar",
        "Edit": "Editar",
        "Refresh": "Actualizar",
        "Search": "Buscar",
        "Connect": "Conectar",
        "Connecting…": "Conectando…",
        "Configure": "Configurar",
        "Applying…": "Aplicando…",
        "Apply Changes": "Aplicar Cambios",
        "Try Again": "Intentar de Nuevo",
        "Copy Commands": "Copiar Comandos",
        "View Instructions": "Ver Instrucciones",
        "Copy IP Address": "Copiar Dirección IP",
        "No changes were made": "No se realizaron cambios",
        "Active": "Activo",
        "Inactive": "Inactivo",
        "Connected": "Conectado",
        "Disconnected": "Desconectado",

        # Main Window
        "Server Information": "Información del Servidor",
        "IP Address": "Dirección IP",
        "Detecting…": "Detectando…",
        "Active Sessions": "Sesiones Activas",
        "0 sessions": "0 sesiones",
        "{count} active sessions": "{count} sesiones activas",
        "Health & Diagnostics": "Salud y Diagnósticos",
        "Health report is not ready yet": "El informe de salud aún no está listo",
        "Check system health now": "Verificar salud del sistema ahora",
        "Healthy · {count} checks passed": "Saludable · {count} verificaciones superadas",
        "{count} critical issue(s)": "{count} problema(s) crítico(s)",
        "{count} warning(s)": "{count} advertencia(s)",
        "{count} check(s) unavailable": "{count} verificación(es) no disponible(s)",
        "Search users...": "Buscar usuarios...",
        "Create a new RDP user": "Crear nuevo usuario RDP",
        "No RDP Users": "Sin usuarios RDP",
        "Add your first RDP user to start managing sessions": "Agregue su primer usuario RDP para comenzar a administrar sesiones",
        "New User": "Nuevo Usuario",
        "Users": "Usuarios",
        "Delete User": "Eliminar Usuario",
        "Are you sure you want to delete user \"{username}\"?": "¿Está seguro de que desea eliminar al usuario \"{username}\"?",
        "This action cannot be undone and will delete the user's home directory.": "Esta acción no se puede deshacer y eliminará el directorio principal del usuario.",
        "User {username} enabled": "Usuario {username} habilitado",
        "Error enabling user {username}": "Error al habilitar el usuario {username}",
        "User {username} disabled": "Usuario {username} deshabilitado",
        "Error disabling user {username}": "Error al deshabilitar el usuario {username}",
        "Error changing status of user {username}": "Error al cambiar el estado del usuario {username}",
        "RDP password cannot be empty": "La contraseña RDP no puede estar vacía",
        "Passwords do not match": "Las contraseñas no coinciden",
        "Repairing {username}; authenticate once...": "Reparando {username}; autentíquese una vez...",
        "Sudo privileges granted—reconnect to apply": "Privilegios de sudo concedidos — reconéctese para aplicar",
        "Error granting sudo privileges to {username}": "Error al conceder privilegios de sudo a {username}",
        "Sudo privileges revoked—reconnect to apply": "Privilegios de sudo revocados — reconéctese para aplicar",
        "Error revoking sudo privileges from {username}": "Error al revocar privilegios de sudo de {username}",
        "Error changing sudo privileges for {username}": "Error al cambiar privilegios de sudo para {username}",
        "Ending sessions for {username}...": "Finalizando sesiones de {username}...",
        "Removing user {username}...": "Eliminando usuario {username}...",
        "User {username} removed successfully": "Usuario {username} eliminado con éxito",
        "Error removing user {username}": "Error al eliminar el usuario {username}",
        "No executables found": "No se encontraron ejecutables",
        "Executable selected": "Ejecutable seleccionado",
        "Application command cannot be empty for RemoteApp": "El comando de la aplicación no puede estar vacío para RemoteApp",
        "Executable path cannot be empty for Windows RemoteApp": "La ruta del ejecutable no puede estar vacía para Windows RemoteApp",
        "File not found: {path}": "Archivo no encontrado: {path}",
        "Username cannot be empty": "El nombre de usuario no puede estar vacío",
        "Password must be at least 6 characters long": "La contraseña debe tener al menos 6 caracteres",
        "Error changing full name": "Error al cambiar el nombre completo",
        "Error changing password": "Error al cambiar la contraseña",
        "Error changing session type": "Error al cambiar el tipo de sesión",
        "Error changing application": "Error al cambiar la aplicación",
        "Error updating WineGE executable": "Error al actualizar el ejecutable de WineGE",
        "Error changing arguments": "Error al cambiar los argumentos",
        "Error renaming user": "Error al renombrar el usuario",
        "Settings saved: {changes}": "Configuración guardada: {changes}",
        "Error updating settings": "Error al actualizar la configuración",
        "{connection_string} copied to clipboard": "{connection_string} copiado al portapapeles",
        "Password cannot be empty": "La contraseña no puede estar vacía",
        "FreeRDP not found": "FreeRDP no encontrado",
        "Opening RemoteApp: {app_name}...": "Abriendo RemoteApp: {app_name}...",
        "Opening {cmd}...": "Abriendo {cmd}...",
        "Error opening FreeRDP: {error}": "Error al abrir FreeRDP: {error}",
        "IP {ip} copied to clipboard": "IP {ip} copiada al portapapeles",

        # Preferences
        "RDP Server Port": "Puerto del Servidor RDP",
        "Default port configuration for RDP client connections": "Configuración del puerto predeterminado para conexiones RDP",
        "Default Port": "Puerto Predeterminado",
        "Port used by RDP users (default: 3389)": "Puerto usado por usuarios RDP (predeterminado: 3389)",
        "Server & Capacity": "Servidor y Capacidad",
        "Session Allocation": "Asignación de Sesiones",
        "Concurrent session limits and resource reservation": "Límites de sesiones simultáneas y reserva de recursos",
        "Linux Session Slots": "Espacios de Sesión Linux",
        "1,280 MB RAM per slot (linux-light)": "1.280 MB de RAM por espacio (linux-light)",
        "Windows / Wine Session Slots": "Espacios de Sesión Windows / Wine",
        "2,560 MB RAM per slot (windows-standard)": "2.560 MB de RAM por espacio (windows-standard)",
        "Max Concurrent Sessions": "Máximo de Sesiones Simultáneas",
        "Global ceiling for active RDP sessions": "Límite global para sesiones RDP activas",
        "Host Memory Reserve (%)": "Reserva de Memoria del Host (%)",
        "RAM reserved for system OS operations": "RAM reservada para operaciones del sistema operativo",
        "Memory Safety Budget": "Presupuesto Seguro de Memoria",
        "Allocated Memory": "Memoria Asignada",
        "Network Access Restriction": "Restricción de Acceso a la Red",
        "Restrict RDP access to a specific private network or VPN": "Restringir acceso RDP a una red privada o VPN específica",
        "Allowed Network (CIDR)": "Red Permitida (CIDR)",
        "Capacity Management": "Gestión de Capacidad",
        "Auto-Detect Safe Capacity": "Autodetectar Capacidad Segura",
        "Automatically compute safe slots based on host RAM": "Calcular espacios seguros automáticamente según la RAM",
        "Recommend": "Recomendar",
        "Apply Server Profile": "Aplicar Perfil de Servidor",
        "Save settings and update system resource limits": "Guardar configuración y actualizar límites de recursos del sistema",
        "✓ Safe Budget": "✓ Presupuesto Seguro",
        "⚠ Exceeds RAM": "⚠ Excede la RAM",
        "Server profile applied successfully": "Perfil del servidor aplicado con éxito",
        "Please enter an allowed network in CIDR format (e.g., 192.168.1.0/24)": "Ingrese la red permitida en formato CIDR (ej: 192.168.1.0/24)",
        "Invalid network format. Use CIDR notation like 192.168.1.0/24": "Formato de red no válido. Use notación CIDR como 192.168.1.0/24",

        # User Dialog
        "Create New RDP User": "Crear Nuevo Usuario RDP",
        "Basic Information": "Información Básica",
        "Username": "Nombre de Usuario",
        "Full Name": "Nombre Completo",
        "Security": "Seguridad",
        "Password": "Contraseña",
        "Confirm Password": "Confirmar Contraseña",
        "Session Type": "Tipo de Sesión",
        "Connection Mode": "Modo de Conexión",
        "Choose between a full desktop or a single application": "Elija entre un escritorio completo o una sola aplicación",
        "Full Desktop": "Escritorio Completo",
        "RemoteApp (Linux Application)": "RemoteApp (Aplicación Linux)",
        "Windows RemoteApp (umu)": "Windows RemoteApp (umu)",
        "Desktop Environment": "Entorno de Escritorio",
        "Install Desktop Environment": "Instalar Entorno de Escritorio",
        "Automatically install if not present on the system": "Instalar automáticamente si no está presente en el sistema",
        "Application": "Aplicación",
        "Select Application": "Seleccionar Aplicación",
        "Custom Application Command": "Comando de Aplicación Personalizado",
        "Application Arguments (Optional)": "Argumentos de la Aplicación (Opcional)",
        "Windows Executable (.exe)": "Ejecutable de Windows (.exe)",
        "Select .exe File": "Seleccionar Archivo .exe",
        "Executable Path": "Ruta del Ejecutable",
        "Auto-start Application": "Iniciar Aplicación Automáticamente",
        "Start application automatically on session connect": "Iniciar la aplicación automáticamente al conectar la sesión",
        "User created successfully": "Usuario creado con éxito",
        "Error creating user: {error}": "Error al crear usuario: {error}",
        "Creating user...": "Creando usuario...",
        "Installing Desktop Environment...": "Instalando Entorno de Escritorio...",

        # Health Dialog
        "System Health": "Salud del Sistema",
        "All statuses": "Todos los estados",
        "Healthy": "Saludable",
        "Warning": "Advertencia",
        "Critical": "Crítico",
        "Unknown": "Desconocido",
        "All components": "Todos los componentes",
        "Host": "Host",
        "User": "Usuario",
        "Session": "Sesión",
        "Windows runtime": "Entorno Windows",
        "Search user, check, or evidence…": "Buscar usuario, verificación o evidencia…",
        "No checks match the selected filters.": "Ninguna verificación coincide con los filtros seleccionados.",
        "Check": "Verificación",
        "Component": "Componente",
        "Status": "Estado",
        "Evidence": "Evidencia",
        "Remediation": "Corrección",
        "Repair": "Reparar",
        "Fix": "Corregir",
        "Running health check…": "Ejecutando verificación de salud…",

        # Connection Sources Dialog
        "Connection Sources": "Fuentes de Conexión",
        "Manage connection profiles and sources for user": "Administrar perfiles y fuentes de conexión para el usuario",
        "Add Profile": "Agregar Perfil",
        "Edit Profile": "Editar Perfil",
        "Delete Profile": "Eliminar Perfil",
        "Profile Name": "Nombre del Perfil",
        "Export .rdp File": "Exportar Archivo .rdp",
        "Exported .rdp file successfully": "Archivo .rdp exportado con éxito",
        "Error exporting .rdp file": "Error al exportar archivo .rdp",

        # Application / Installation Dialogs
        "xrdp Server Not Found": "Servidor xrdp No Encontrado",
        "The xrdp server is required to create remote RDP sessions.\n\nWould you like to install it now?": "El servidor xrdp es necesario para crear sesiones RDP remotas.\n\n¿Desea instalarlo ahora?",
        "Install xrdp": "Instalar xrdp",
        "Installing xrdp": "Instalando xrdp",
        "Installing the RDP server...\nThis may take a few minutes.": "Instalando el servidor RDP...\nEsto puede tardar unos minutos.",
        "Preparing installation...": "Preparando instalación...",
        "Installation complete!": "¡Instalación completada!",
        "Installation error": "Error de instalación",
        "xrdp Installed Successfully": "¡xrdp Instalado con Éxito!",
        "The xrdp server was installed and configured successfully.\n\nYou can now create RDP users!": "El servidor xrdp se instaló y configuró con éxito.\n\n¡Ahora puede crear usuarios RDP!",
        "xrdp Installation Error": "Error de Instalación de xrdp",
        "Manual xrdp Installation": "Instalación Manual de xrdp",
        "Commands copied to the clipboard!": "¡Comandos copiados al portapapeles!",
        "Installing FreeRDP": "Instalando FreeRDP",
        "Installing the RDP client...\nThis may take a few minutes.": "Instalando el cliente RDP...\nEsto puede tardar unos minutos.",
        "FreeRDP Installed Successfully": "¡FreeRDP Instalado con Éxito!",
        "The FreeRDP client was installed successfully.\n\nYou can now connect to your RDP users!": "El cliente FreeRDP se instaló con éxito.\n\n¡Ahora puede conectarse a sus usuarios RDP!",
        "FreeRDP Installation Error": "Error de Instalación de FreeRDP",
    },
}

# Alias mapping for regional variants (e.g., pt -> pt_BR)
LANGUAGE_ALIASES: Dict[str, str] = {
    "pt": "pt_BR",
    "pt_PT": "pt_BR",
    "es_ES": "es",
    "es_MX": "es",
    "es_AR": "es",
    "es_CL": "es",
    "es_CO": "es",
}

_current_language: Optional[str] = None


def detect_system_language() -> str:
    """
    Detect the operating system language from environment or locale settings.
    Falls back to 'en' if not detected or unsupported.
    """
    for env_var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(env_var)
        if val:
            val_clean = val.strip()
            if val_clean in ("C", "POSIX") or val_clean.startswith("en"):
                return "en"
            # Extract language code (e.g., 'pt_BR.UTF-8' -> 'pt_BR')
            clean = val_clean.split(".")[0].split("@")[0].strip()
            if clean in TRANSLATIONS:
                return clean
            if clean in LANGUAGE_ALIASES and LANGUAGE_ALIASES[clean] in TRANSLATIONS:
                return LANGUAGE_ALIASES[clean]
            # Try 2-letter prefix (e.g., 'pt' from 'pt_BR')
            prefix = clean.split("_")[0]
            if prefix in TRANSLATIONS:
                return prefix
            if prefix in LANGUAGE_ALIASES and LANGUAGE_ALIASES[prefix] in TRANSLATIONS:
                return LANGUAGE_ALIASES[prefix]

    try:
        loc = locale.getlocale()[0]
        if loc:
            if loc in ("C", "POSIX") or loc.startswith("en"):
                return "en"
            if loc in TRANSLATIONS:
                return loc
            if loc in LANGUAGE_ALIASES and LANGUAGE_ALIASES[loc] in TRANSLATIONS:
                return LANGUAGE_ALIASES[loc]
            prefix = loc.split("_")[0]
            if prefix in TRANSLATIONS:
                return prefix
            if prefix in LANGUAGE_ALIASES and LANGUAGE_ALIASES[prefix] in TRANSLATIONS:
                return LANGUAGE_ALIASES[prefix]
    except Exception:
        pass

    return "en"


def get_current_language() -> str:
    """Get the active language code."""
    global _current_language
    if _current_language is None:
        _current_language = detect_system_language()
    return _current_language


def set_language(lang_code: str) -> None:
    """Set the active language code explicitly."""
    global _current_language
    resolved = LANGUAGE_ALIASES.get(lang_code, lang_code)
    _current_language = resolved


def register_language(lang_code: str, catalog: Dict[str, str]) -> None:
    """
    Register or extend a language translation catalog.
    
    Example:
        register_language('fr', {'Cancel': 'Annuler', 'OK': 'D\'accord'})
    """
    if lang_code not in TRANSLATIONS:
        TRANSLATIONS[lang_code] = {}
    TRANSLATIONS[lang_code].update(catalog)


def get_available_languages() -> List[str]:
    """List all supported language codes."""
    return sorted(list(TRANSLATIONS.keys()) + ["en"])


def get_text(message: str, **kwargs) -> str:
    """
    Translate a message string into the currently active language.
    If no translation is found, the original message string is returned.
    Supports optional format placeholders (e.g., get_text("Hello {name}", name="John")).
    """
    lang = get_current_language()
    translated = message

    if lang != "en" and lang in TRANSLATIONS:
        translated = TRANSLATIONS[lang].get(message, message)

    if kwargs:
        try:
            return translated.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return translated

    return translated


# Shorthand alias commonly used in Python / GTK applications
_ = get_text
