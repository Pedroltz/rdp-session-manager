export type Locale = "pt" | "en";
export type DemoMode = "desktop" | "linux" | "windows";

type Feature = { eyebrow: string; title: string; body: string; accent: "pink" | "cream" | "mint" };
type Faq = { question: string; answer: string };
type DemoCopy = { label: string; title: string; session: string; command: string; status: string; detail: string };

export type SiteContent = {
  locale: Locale;
  langName: string;
  nav: { features: string; story: string; compatibility: string; install: string; github: string };
  hero: { kicker: string; title: string; accent: string; body: string; install: string; github: string; proof: string };
  story: {
    kicker: string;
    title: string;
    body: string;
    legacy: string;
    legacyDetail: string;
    server: string;
    serverDetail: string;
    access: string;
    accessDetail: string;
    clients: string[];
  };
  demo: { kicker: string; title: string; body: string; modes: Record<DemoMode, DemoCopy>; user: string; sessionType: string; app: string; active: string };
  features: { kicker: string; title: string; body: string; items: Feature[] };
  compatibility: { kicker: string; title: string; body: string; distros: string; desktops: string; clients: string; verified: string };
  install: { kicker: string; title: string; body: string; copy: string; copied: string; requirements: string; reqBody: string; docs: string; releases: string };
  openSource: { kicker: string; title: string; body: string; cta: string };
  faq: { kicker: string; title: string; items: Faq[] };
  footer: string;
};

const pt: SiteContent = {
  locale: "pt",
  langName: "English",
  nav: { features: "Recursos", story: "Como funciona", compatibility: "Compatibilidade", install: "Instalação", github: "GitHub" },
  hero: {
    kicker: "Administração RDP nativa para Linux",
    title: "Leve aplicações Windows para qualquer tela.",
    accent: "Sem reescrever o legado.",
    body: "Gerencie usuários, desktops e RemoteApps em servidores Linux por uma interface GTK moderna — com WineGE para publicar aplicações Windows via RDP.",
    install: "Instalar agora",
    github: "Ver no GitHub",
    proof: "GTK 4  •  libadwaita  •  xrdp  •  WineGE  •  GPL-3.0"
  },
  story: {
    kicker: "Uma aplicação. Cinco portas de entrada.",
    title: "O legado fica no servidor. A experiência chega ao usuário.",
    body: "O RDP Session Manager transforma uma infraestrutura difícil de operar em um fluxo visual, seguro e repetível.",
    legacy: "Aplicação Windows",
    legacyDetail: "O executável e seu ambiente continuam preservados.",
    server: "Servidor Linux",
    serverDetail: "WineGE executa. xrdp entrega. Você administra.",
    access: "Acesso RDP",
    accessDetail: "O usuário recebe a aplicação, não a complexidade.",
    clients: ["Windows", "Linux", "macOS", "Android", "iOS"]
  },
  demo: {
    kicker: "A infraestrutura virou produto",
    title: "GUI para pessoas. CLI para automação.",
    body: "Alterne entre a experiência Desktop e a CLI. Na interface, configure sessões visualmente; no terminal, acompanhe os mesmos recursos sendo executados por comandos reais.",
    modes: {
      desktop: { label: "Desktop completo", title: "Ambiente de trabalho remoto", session: "GNOME Desktop", command: "gnome-session-flashback", status: "Sessão pronta", detail: "Desktop completo com GNOME, KDE Plasma ou XFCE." },
      linux: { label: "Linux RemoteApp", title: "Aplicação Linux isolada", session: "Linux RemoteApp", command: "libreoffice --writer", status: "Aplicação publicada", detail: "APT, Snap e Flatpak com janela remota dedicada." },
      windows: { label: "Windows RemoteApp", title: "Aplicação Windows no Linux", session: "WineGE RemoteApp", command: "C:\\Program Files\\LegacyApp\\app.exe", status: "WineGE conectado", detail: "Prefixo Wine isolado por usuário e configuração automática." }
    },
    user: "Usuário RDP",
    sessionType: "Tipo de sessão",
    app: "Comando da aplicação",
    active: "Ativo"
  },
  features: {
    kicker: "Tudo em um só lugar",
    title: "Operação simples. Engenharia séria.",
    body: "Da criação do usuário à sessão em produção, cada camada foi pensada para reduzir atrito sem esconder o que importa.",
    items: [
      { eyebrow: "01 — Controle", title: "Usuários e sessões", body: "Crie, remova, habilite e monitore contas RDP e encerre sessões ativas.", accent: "pink" },
      { eyebrow: "02 — RemoteApp", title: "Uma janela, não um desktop", body: "Publique Firefox, LibreOffice ou qualquer aplicação Linux compatível.", accent: "cream" },
      { eyebrow: "03 — WineGE", title: "Windows sem reescrita", body: "Instaladores e executáveis portáteis em prefixos isolados por usuário.", accent: "mint" },
      { eyebrow: "04 — Automação", title: "CLI completa", body: "A mesma lógica da GUI disponível para scripts, JSON e rotinas operacionais.", accent: "cream" },
      { eyebrow: "05 — Segurança", title: "Privilégios explícitos", body: "PolicyKit e helpers especializados separam a interface das operações administrativas.", accent: "mint" },
      { eyebrow: "06 — Instalação", title: "Multi-distribuição", body: "Dependências, xrdp e FreeRDP verificados em Ubuntu, Debian, Arch e derivados.", accent: "pink" }
    ]
  },
  compatibility: {
    kicker: "Feito para o Linux real",
    title: "Do servidor à tela do usuário.",
    body: "Ambientes, formatos de aplicação e clientes diferentes — uma camada central de administração.",
    distros: "Distribuições",
    desktops: "Desktops",
    clients: "Clientes RDP",
    verified: "Fluxos críticos validados por testes end-to-end com xrdp e FreeRDP."
  },
  install: {
    kicker: "Comece agora",
    title: "Um comando. Uma infraestrutura operável.",
    body: "O instalador oficial detecta a distribuição, valida os artefatos e orienta a instalação das dependências.",
    copy: "Copiar comando",
    copied: "Copiado!",
    requirements: "Requisitos",
    reqBody: "Ubuntu 22.04+, Debian 12+, Arch Linux ou derivados suportados. Python 3.9+, GTK 4, libadwaita e PolicyKit.",
    docs: "Ler documentação",
    releases: "Ver releases"
  },
  openSource: {
    kicker: "Aberto por escolha",
    title: "Infraestrutura que você pode entender, auditar e melhorar.",
    body: "O RDP Session Manager é GPL-3.0. O código, a documentação, os testes e o processo de release vivem em público.",
    cta: "Explorar o projeto"
  },
  faq: {
    kicker: "Perguntas frequentes",
    title: "Antes de colocar em produção.",
    items: [
      { question: "O aplicativo roda no Windows?", answer: "O painel administrativo roda no servidor Linux. Windows, macOS, Linux, Android e iOS podem acessar as sessões por um cliente RDP compatível." },
      { question: "Qualquer aplicação Windows funciona?", answer: "A compatibilidade depende do WineGE e da aplicação. Softwares que exigem drivers próprios, anti-cheat ou recursos específicos de DirectX 12 podem não funcionar." },
      { question: "É necessário publicar um desktop completo?", answer: "Não. É possível entregar um desktop GNOME, KDE ou XFCE, uma única aplicação Linux ou uma aplicação Windows executada com WineGE." },
      { question: "Posso automatizar a administração?", answer: "Sim. A CLI cobre usuários, sessões, desktops, dependências, servidor e configuração, com saída em tabela ou JSON." }
    ]
  },
  footer: "RDP Session Manager — criado para tornar a infraestrutura RDP no Linux mais simples de operar."
};

const en: SiteContent = {
  locale: "en",
  langName: "Português",
  nav: { features: "Features", story: "How it works", compatibility: "Compatibility", install: "Install", github: "GitHub" },
  hero: {
    kicker: "Native RDP administration for Linux",
    title: "Bring Windows applications to any screen.",
    accent: "Without rewriting the legacy.",
    body: "Manage users, desktops and RemoteApps on Linux servers through a modern GTK interface — with WineGE to publish Windows applications over RDP.",
    install: "Install now",
    github: "View on GitHub",
    proof: "GTK 4  •  libadwaita  •  xrdp  •  WineGE  •  GPL-3.0"
  },
  story: {
    kicker: "One application. Five entry points.",
    title: "The legacy stays on the server. The experience reaches the user.",
    body: "RDP Session Manager turns difficult infrastructure into a visual, secure and repeatable workflow.",
    legacy: "Windows application",
    legacyDetail: "The executable and its environment remain preserved.",
    server: "Linux server",
    serverDetail: "WineGE runs it. xrdp delivers it. You manage it.",
    access: "RDP access",
    accessDetail: "The user gets the application, not the complexity.",
    clients: ["Windows", "Linux", "macOS", "Android", "iOS"]
  },
  demo: {
    kicker: "Infrastructure became a product",
    title: "GUI for people. CLI for automation.",
    body: "Switch between the Desktop experience and the CLI. Configure sessions visually in the interface, then watch the same capabilities run through real commands in the terminal.",
    modes: {
      desktop: { label: "Full desktop", title: "Remote desktop environment", session: "GNOME Desktop", command: "gnome-session-flashback", status: "Session ready", detail: "A complete GNOME, KDE Plasma or XFCE desktop." },
      linux: { label: "Linux RemoteApp", title: "Isolated Linux application", session: "Linux RemoteApp", command: "libreoffice --writer", status: "Application published", detail: "APT, Snap and Flatpak with a dedicated remote window." },
      windows: { label: "Windows RemoteApp", title: "Windows application on Linux", session: "WineGE RemoteApp", command: "C:\\Program Files\\LegacyApp\\app.exe", status: "WineGE connected", detail: "An isolated Wine prefix per user with automatic setup." }
    },
    user: "RDP user",
    sessionType: "Session type",
    app: "Application command",
    active: "Active"
  },
  features: {
    kicker: "Everything in one place",
    title: "Simple operation. Serious engineering.",
    body: "From user creation to a live session, every layer is designed to reduce friction without hiding what matters.",
    items: [
      { eyebrow: "01 — Control", title: "Users and sessions", body: "Create, remove, enable and monitor RDP accounts and terminate active sessions.", accent: "pink" },
      { eyebrow: "02 — RemoteApp", title: "A window, not a desktop", body: "Publish Firefox, LibreOffice or any compatible Linux application.", accent: "cream" },
      { eyebrow: "03 — WineGE", title: "Windows without a rewrite", body: "Installers and portable executables in isolated per-user prefixes.", accent: "mint" },
      { eyebrow: "04 — Automation", title: "Complete CLI", body: "The GUI's logic is available for scripts, JSON output and operational routines.", accent: "cream" },
      { eyebrow: "05 — Security", title: "Explicit privileges", body: "PolicyKit and specialized helpers separate the interface from administrative operations.", accent: "mint" },
      { eyebrow: "06 — Installation", title: "Multi-distribution", body: "Dependencies, xrdp and FreeRDP verified on Ubuntu, Debian, Arch and derivatives.", accent: "pink" }
    ]
  },
  compatibility: {
    kicker: "Built for real-world Linux",
    title: "From the server to the user's screen.",
    body: "Different environments, application formats and clients — one central administration layer.",
    distros: "Distributions",
    desktops: "Desktops",
    clients: "RDP clients",
    verified: "Critical workflows validated through end-to-end tests with xrdp and FreeRDP."
  },
  install: {
    kicker: "Get started",
    title: "One command. Operable infrastructure.",
    body: "The official installer detects the distribution, validates release assets and guides dependency installation.",
    copy: "Copy command",
    copied: "Copied!",
    requirements: "Requirements",
    reqBody: "Ubuntu 22.04+, Debian 12+, Arch Linux or supported derivatives. Python 3.9+, GTK 4, libadwaita and PolicyKit.",
    docs: "Read the docs",
    releases: "View releases"
  },
  openSource: {
    kicker: "Open by choice",
    title: "Infrastructure you can understand, audit and improve.",
    body: "RDP Session Manager is GPL-3.0. The code, documentation, tests and release process all live in public.",
    cta: "Explore the project"
  },
  faq: {
    kicker: "Frequently asked questions",
    title: "Before going to production.",
    items: [
      { question: "Does the application run on Windows?", answer: "The administration panel runs on the Linux server. Windows, macOS, Linux, Android and iOS can access sessions through a compatible RDP client." },
      { question: "Will every Windows application work?", answer: "Compatibility depends on WineGE and the application. Software requiring custom drivers, anti-cheat or specific DirectX 12 features may not work." },
      { question: "Do I need to publish a full desktop?", answer: "No. You can deliver a GNOME, KDE or XFCE desktop, a single Linux application, or a Windows application running with WineGE." },
      { question: "Can administration be automated?", answer: "Yes. The CLI covers users, sessions, desktops, dependencies, server and configuration, with table or JSON output." }
    ]
  },
  footer: "RDP Session Manager — built to make RDP infrastructure on Linux easier to operate."
};

export const content: Record<Locale, SiteContent> = { pt, en };
