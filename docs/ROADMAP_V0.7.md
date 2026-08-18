# RDP Session Manager v0.7 — Centro de Operações

## Resumo

Transformar o projeto em uma ferramenta confiável para administrar um único
servidor empresarial com até 25 sessões. A v0.7 continuará usando GTK + CLI,
contas Linux locais e confirmação explícita antes de qualquer reparo.

O foco será consolidar diagnóstico, reparo guiado e auditoria. Console web,
LDAP/Active Directory e gerenciamento de múltiplos servidores ficam fora desta
versão.

## Progresso

- [x] Contrato versionado de saúde com estados e identificadores estáveis.
- [x] Diagnóstico unificado inicial de host, usuários e sessões.
- [x] Comando `rdpsm health` com saída em tabela ou JSON.
- [x] Resumo assíncrono de saúde na tela principal GTK.
- [x] Visão GTK com detalhes, filtros combináveis e evidências expansíveis.
- [x] Planos de reparo serializáveis com confirmação e revalidação.
- [x] Backup e rollback transacional dos arquivos gerenciados em reparos.
- [x] Auditoria privilegiada e exportação JSONL para reparos de usuário.
- [x] Ampliar a auditoria para as demais operações privilegiadas mutáveis.
- [x] CI contínua e cenários E2E adicionais.

## Implementação principal

### Modelo unificado de saúde

- Criar um serviço de diagnóstico separado dos atuais `UserManager`,
  `ServerManager` e `SessionMonitor`, evitando aumentar arquivos que já
  ultrapassam mil linhas.
- Padronizar o resultado com `schema_version`, horário, estado geral e
  verificações contendo:
  - identificador estável;
  - escopo `host`, `user`, `session` ou `windows-runtime`;
  - estado `healthy`, `warning`, `critical` ou `unknown`;
  - resumo, evidências e ação corretiva disponível.
- Verificar serviços xrdp, TLS e validade do certificado, firewall, cgroup v2,
  espaço em disco, memória, capacidade, configuração, permissões, perfis,
  dispatcher, runtime Windows e sessões abandonadas.
- Separar atividade de falha: um usuário conectado não será considerado
  insalubre apenas por possuir processos.
- Manter compatibilidade com perfis v2 e WineGE legado.

### Centro de Operações GTK

- Evoluir a tela principal para mostrar saúde geral, serviços, capacidade e
  alertas, mantendo a lista atual de usuários.
- Adicionar uma página de diagnóstico com filtros por severidade, usuário e
  componente.
- Executar verificações em segundo plano, exibir horário da última atualização
  e permitir “Verificar agora”.
- Para cada problema reparável, mostrar:
  - causa e evidências;
  - alterações planejadas;
  - necessidade de desconectar sessões;
  - backup/rollback disponível;
  - botão de confirmação antes da autenticação administrativa.
- Exibir resultado detalhado do reparo e atualizar imediatamente o estado da
  tela.

### CLI e compatibilidade

- Adicionar `rdpsm health [--user USER] [--format table|json]`.
- Estender `rdpsm user diagnose` para retornar o mesmo modelo da GUI.
- Alterar `rdpsm user repair` para apresentar o plano antes da confirmação;
  oferecer `--plan` para inspeção não mutável e `--yes` para automação
  explícita.
- Manter `server status`, `server preflight` e os comandos antigos funcionando,
  delegando internamente ao novo serviço quando aplicável.
- Usar códigos de saída: `0` saudável, `1` warning/critical e `2` erro de uso ou
  diagnóstico indisponível.

### Reparos e auditoria

- Representar cada reparo por um plano serializável com precondições, etapas,
  impacto, reversibilidade e necessidade de privilégio.
- Revalidar as precondições imediatamente antes de aplicar; rejeitar planos que
  ficaram obsoletos.
- Fazer backup antes de mudanças em perfis, wrappers ou configuração e
  restaurar automaticamente se uma etapa falhar.
- Registrar operações administrativas em
  `/var/log/rdp-session-manager/audit.jsonl`, gravado somente pelo processo
  privilegiado.
- Cada evento terá ID, UTC, ator derivado de `SUDO_UID`/`PKEXEC_UID`, ação,
  alvo, resultado, código de erro e ID do plano. Senhas, tokens e argumentos
  sensíveis nunca serão registrados.
- Adicionar `rdpsm audit list` e `rdpsm audit export --output ARQUIVO`, com
  filtros por período, usuário, ação e resultado.
- Configurar rotação dos logs no instalador. Esta trilha será operacional e
  exportável para SIEM, mas não será apresentada como armazenamento inviolável
  de conformidade.

### Qualidade e documentação

- Restaurar CI para pull requests com testes unitários, sintaxe dos helpers,
  validação de pacotes e checagem de schemas.
- Executar testes RDP/Windows E2E em workflow agendado ou antes de releases,
  pois exigem ambiente privilegiado.
- Atualizar o troubleshooting, removendo itens já implementados e ligando cada
  diagnóstico aos seus códigos e reparos.
- Documentar formato JSON, códigos de saída, política de auditoria e
  procedimento de rollback.

## Testes e critérios de aceitação

- A suíte completa continua passando; o primeiro incremento elevou a cobertura
  de 194 para 202 testes.
- Testes novos cobrem serviço xrdp parado, TLS ausente ou próximo da expiração,
  perfil corrompido, wrapper divergente, runtime Windows incompleto,
  disco/memória críticos e sessão abandonada.
- Usuário conectado e saudável permanece `healthy`.
- GUI e CLI produzem os mesmos IDs, severidades e evidências para o mesmo
  snapshot.
- A GUI continua responsiva durante diagnóstico e reparo.
- Reparos são idempotentes, rejeitam precondições obsoletas e restauram backup
  em falha simulada.
- Toda operação mutável gera evento de sucesso ou falha, sem segredos.
- Teste E2E cria um usuário com Desktop + aplicativo Windows, abre o seletor
  GTK, executa cada perfil e confirma o encerramento correto da sessão.

## Roadmap posterior

- **v0.8 — Segurança e manutenção:** broker privilegiado único com operações
  permitidas, políticas de senha/expiração, quotas de disco, i18n com português
  e inglês e refatoração gradual de `cli.py`, `user_manager.py` e
  `main_window.py`.
- **v0.9 — Automação empresarial:** configuração declarativa importável,
  agendamento de verificações, notificações, integração opcional com
  syslog/SIEM e backup/restauração completo do servidor.
- **v1.0+:** avaliar console web, LDAP/Active Directory e gerenciamento de
  múltiplos hosts somente após estabilizar o modelo local.

## Premissas

- Primeira meta: um host Ubuntu/Debian com até 25 sessões; Arch continua
  experimental.
- Administração por GTK local e CLI headless.
- Contas Linux locais endurecidas; sem LDAP/Active Directory nesta etapa.
- Nenhum reparo é aplicado automaticamente: sempre há plano, confirmação e
  autenticação.
- Os diretórios locais de backup existentes permanecem fora do versionamento.
