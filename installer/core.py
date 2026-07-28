#!/usr/bin/env python3
"""Friendly, transparent and idempotent installer for RDP Session Manager."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.text import Text
except ImportError as exc:
    print(
        "O instalador visual precisa da biblioteca Rich.\n"
        "Execute pelo install.sh da release ou instale localmente com:\n"
        "  python3 -m pip install -r installer/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


REPOSITORY = "Pedroltz/rdp-session-manager"
API_BASE = f"https://api.github.com/repos/{REPOSITORY}"
DOWNLOAD_BASE = f"https://github.com/{REPOSITORY}/releases"
APP_DEB = "rdp-session-manager.deb"
APP_ARCH = "rdp-session-manager.pkg.tar.zst"
SUPPORTED_UBUNTU = (22, 4)
SUPPORTED_DEBIAN = 12


class InstallerError(RuntimeError):
    """An expected, user-actionable installer failure."""


@dataclass(frozen=True)
class Distro:
    family: str
    identifier: str
    version: str
    name: str
    id_like: tuple[str, ...]


class ActivityStatus:
    """Adapter that can switch a Rich task from pulsing to real progress."""

    def __init__(self, progress: Progress, task_id: int) -> None:
        self.progress = progress
        self.task_id = task_id

    def update(self, description: str) -> None:
        self.progress.update(self.task_id, description=description)

    def update_progress(self, description: str, completed: int, total: int) -> None:
        self.progress.update(
            self.task_id,
            description=description,
            completed=completed,
            total=total,
        )


class UI:
    def __init__(self, verbose: bool = False, dry_run: bool = False) -> None:
        self.verbose = verbose
        self.dry_run = dry_run
        self.console = Console(highlight=False)
        self.overall: Optional[Progress] = None
        self.overall_task: Optional[int] = None
        self._closed = False
        mode = "Pré-visualização: nenhuma alteração será realizada." if dry_run else "Vamos preparar este computador para gerenciar sessões RDP."
        title = Text("RDP Session Manager", style="bold bright_cyan")
        body = Text.assemble(
            ("Assistente de instalação e configuração\n", "bold white"),
            ("Instale a aplicação, configure o servidor xrdp e escolha os recursos opcionais.\n", "white"),
            (mode, "dim"),
        )
        self.console.print(Panel(body, title=title, border_style="bright_cyan", padding=(1, 3)))

    def info(self, message: str) -> None:
        self.console.print(Text(message, style="cyan"))

    def stage(self, number: int, total: int, title: str) -> None:
        if self.overall is None:
            self.overall = Progress(
                SpinnerColumn(style="bright_cyan", finished_text="[green]✓[/]"),
                TextColumn("[bold cyan]{task.description}", justify="left"),
                BarColumn(
                    bar_width=None,
                    complete_style="bright_cyan",
                    finished_style="bright_green",
                    pulse_style="cyan",
                ),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
                expand=True,
            )
            self.overall.start()
            self.overall_task = self.overall.add_task(title, total=total, completed=0)
        assert self.overall_task is not None
        self.overall.update(self.overall_task, description=f"Etapa {number}/{total} · {title}", completed=number - 1)

    def command_line(self, line: str) -> None:
        if self.verbose:
            self.console.print(Text(f"$ {line.removeprefix('$ ')}", style="dim"))

    @contextmanager
    def running(self, label: str) -> Generator[ActivityStatus, None, None]:
        with Progress(
            SpinnerColumn(style="bright_cyan", finished_text="[green]✓[/]"),
            TextColumn("{task.description}", justify="left"),
            BarColumn(
                bar_width=None,
                complete_style="bright_magenta",
                finished_style="bright_green",
                pulse_style="bright_cyan",
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
            expand=True,
        ) as progress:
            task = progress.add_task(f"[bold cyan]{label}[/]", total=None)
            yield ActivityStatus(progress, task)

    def command_output(self, message: str, status: ActivityStatus) -> None:
        lowered = message.lower()
        fraction = parse_progress_fraction(message)
        if fraction:
            completed, total = fraction
            label = re.sub(r"^\s*\(\s*\d+\s*/\s*\d+\s*\)\s*", "", message).strip()
            label = re.sub(r"(?i)^progress:\s*\[\s*\d+%\s*\]\s*", "", label).strip()
            label = label if label else "Processando"
            compact = label if len(label) <= 72 else f"…{label[-71:]}"
            status.update_progress(f"[bold cyan]{compact}[/]", completed, total)
        if self.verbose:
            self.console.print(Text(f"  {message}"))
        elif any(token in lowered for token in ("erro", "error", "failed", "falha", "warning", "aviso")):
            self.console.print(Text(f"  {message}", style="yellow"))
        elif not fraction:
            compact = message if len(message) <= 100 else f"…{message[-99:]}"
            status.update(f"[bold cyan]Processando[/] [dim]{compact}[/]")

    def show_plan(self, rows: Sequence[tuple[str, str]], packages: Sequence[str]) -> None:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold bright_cyan", no_wrap=True)
        table.add_column(style="white")
        for label, value in rows:
            table.add_row(label, value)
        package_text = Text(", ".join(packages), style="dim")
        self.console.print(Panel(table, title="[bold]Plano de instalação[/]", border_style="blue"))
        self.console.print(Panel(package_text, title=f"[bold]Pacotes ({len(packages)})[/]", border_style="dim"))

    def confirm(self, question: str) -> bool:
        live_was_running = bool(
            self.overall is not None
            and getattr(self.overall.live, "is_started", False)
        )
        if live_was_running:
            self.overall.stop()
        try:
            return Prompt.ask(question, choices=["s", "n"], default="n", console=self.console) == "s"
        finally:
            if live_was_running and self.overall is not None:
                self.overall.start()

    def component_prompt(self, question: str, description: str, *, default: bool) -> bool:
        self.console.print()
        self.console.print(f"[bold white]{question}[/]")
        self.console.print(Text(description, style="dim"))
        selected = Prompt.ask(
            "Selecionar este componente?",
            choices=["s", "n"],
            default="s" if default else "n",
            console=self.console,
        )
        return selected == "s"

    def success(self, message: str) -> None:
        self.console.print(f"[bold green]✓[/] {message}")

    def warning(self, message: str) -> None:
        self.console.print(Panel(Text(message), title="[bold yellow]Atenção[/]", border_style="yellow"))

    def error(self, message: str) -> None:
        self.console.print(Panel(Text(message), title="[bold red]Falha na instalação[/]", border_style="red"))

    def complete(self, description: str = "Instalação concluída") -> None:
        if self.overall is not None and self.overall_task is not None:
            self.overall.update(self.overall_task, completed=5, description=description)
        self.close()

    def close(self) -> None:
        if not self._closed and self.overall is not None:
            self.overall.stop()
        self._closed = True


class InstallLog:
    def __init__(self) -> None:
        path = Path.home() / ".local" / "state" / "rdp-session-manager" / "install.log"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("a", encoding="utf-8")
        except OSError:
            # Read-only home directories are common in CI, containers and
            # immutable desktops. Keep diagnostics available in that case.
            path = Path(tempfile.gettempdir()) / "rdp-session-manager-install.log"
            handle = path.open("a", encoding="utf-8")
        self.path = path
        self.handle = handle
        self.write(f"\n=== installer started {time.strftime('%Y-%m-%d %H:%M:%S')} ===")

    def write(self, line: str) -> None:
        self.handle.write(line.rstrip("\n") + "\n")
        self.handle.flush()

    def close(self) -> None:
        self.write("=== installer finished ===")
        self.handle.close()


def parse_os_release(path: Path = Path("/etc/os-release")) -> Mapping[str, str]:
    values: dict[str, str] = {}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    except OSError as exc:
        raise InstallerError(f"Não foi possível ler {path}: {exc}") from exc
    return values


def detect_distro(path: Path = Path("/etc/os-release")) -> Distro:
    values = parse_os_release(path)
    identifier = values.get("ID", "").lower()
    id_like = tuple(x.lower() for x in values.get("ID_LIKE", "").split())
    candidates = (identifier,) + id_like
    if any(x in {"arch", "manjaro", "endeavouros", "cachyos"} for x in candidates):
        family = "arch"
    elif any(x in {"debian", "ubuntu", "linuxmint", "pop"} for x in candidates):
        family = "debian"
    else:
        raise InstallerError(
            f"Distribuição não suportada: {identifier or 'desconhecida'}. "
            "Suportadas: Ubuntu/Debian e derivados, Arch e derivados."
        )
    return Distro(
        family=family,
        identifier=identifier,
        version=values.get("VERSION_ID", "desconhecida"),
        name=values.get("PRETTY_NAME", identifier or "Linux"),
        id_like=id_like,
    )


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def package_lock_held(paths: Iterable[Path]) -> Optional[Path]:
    """Return a package-manager lock that is currently held, if any."""
    for path in paths:
        if not path.exists():
            continue
        try:
            with path.open("a+") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except BlockingIOError:
            return path
        except PermissionError:
            # The package manager will report a real lock later; lack of
            # read/write permission alone must not be reported as a lock.
            continue
        except OSError:
            continue
    return None


def shell_command(command: Sequence[str]) -> str:
    return shlex.join(str(item) for item in command)


def parse_progress_fraction(message: str) -> Optional[tuple[int, int]]:
    """Extract native package-manager progress without inventing percentages."""
    fraction = re.match(r"^\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)", message)
    if fraction:
        completed, total = int(fraction.group(1)), int(fraction.group(2))
        if total > 0 and 0 <= completed <= total:
            return completed, total

    percent = re.search(r"(?i)\bprogress:\s*\[\s*(\d{1,3})%\s*\]", message)
    if not percent:
        percent = re.search(r"(?:^|\s)(\d{1,3})%(?:\s|$)", message)
    if percent:
        completed = int(percent.group(1))
        if 0 <= completed <= 100:
            return completed, 100
    return None


class Runner:
    def __init__(self, ui: UI, log: InstallLog, dry_run: bool = False) -> None:
        self.ui = ui
        self.log = log
        self.dry_run = dry_run

    def run(
        self,
        command: Sequence[str],
        *,
        timeout: int = 1800,
        check: bool = True,
        env: Optional[Mapping[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        rendered = shell_command(command)
        self.ui.command_line(f"$ {rendered}")
        self.log.write(f"$ {rendered}")
        if self.dry_run:
            return subprocess.CompletedProcess(command, 0, "", "")
        try:
            with self.ui.running(f"Executando {command[0]}") as status:
                process = subprocess.Popen(
                    list(command),
                    cwd=str(cwd) if cwd else None,
                    env=dict(env) if env else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                lines: list[str] = []
                assert process.stdout is not None
                deadline = time.monotonic() + timeout
                for line in process.stdout:
                    if time.monotonic() > deadline:
                        process.kill()
                        raise InstallerError(f"Timeout após {timeout}s: {rendered}")
                    clean = line.rstrip()
                    if clean:
                        self.log.write(clean)
                        lines.append(clean)
                        self.ui.command_output(clean, status)
                returncode = process.wait(timeout=max(1, int(deadline - time.monotonic())))
            result = subprocess.CompletedProcess(command, returncode, "\n".join(lines), "")
            if check and returncode != 0:
                raise InstallerError(
                    f"Comando falhou (código {returncode}): {rendered}. "
                    f"Consulte o log: {self.log.path}"
                )
            return result
        except subprocess.TimeoutExpired as exc:
            raise InstallerError(f"Timeout executando: {rendered}. Log: {self.log.path}") from exc
        except OSError as exc:
            raise InstallerError(f"Não foi possível executar {rendered}: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksums(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([0-9a-fA-F]{64})\s+[* ]?(.+?)\s*$", line)
        if match:
            checksums[Path(match.group(2)).name] = match.group(1).lower()
    return checksums


def enable_multilib_config(text: str) -> str:
    """Return pacman.conf content with the official multilib block enabled."""
    if re.search(r"(?m)^[ \t]*\[multilib\][ \t]*(?:#.*)?$", text):
        return text

    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not re.match(r"^[ \t]*#[ \t]*\[multilib\][ \t]*(?:#.*)?(?:\r?\n)?$", line):
            continue
        newline = "\n" if line.endswith("\n") else ""
        indent = re.match(r"^[ \t]*", line).group(0)
        lines[index] = f"{indent}[multilib]{newline}"
        for include_index in range(index + 1, len(lines)):
            stripped = lines[include_index].strip()
            if re.match(r"#?[ \t]*\[.+\]", stripped):
                break
            include = re.match(
                r"^([ \t]*)#[ \t]*(Include[ \t]*=[ \t]*/etc/pacman\.d/mirrorlist[ \t]*)(\r?\n)?$",
                lines[include_index],
            )
            if include:
                lines[include_index] = f"{include.group(1)}{include.group(2)}{include.group(3) or ''}"
                break
        return "".join(lines)

    separator = "" if not text or text.endswith("\n") else "\n"
    return f"{text}{separator}\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n"


def pkgbuild_pgp_keys(text: str) -> list[str]:
    """Extract full PGP fingerprints declared by an AUR PKGBUILD."""
    match = re.search(r"(?ms)^[ \t]*validpgpkeys[ \t]*=[ \t]*\((.*?)\)", text)
    if not match:
        return []
    return list(dict.fromkeys(key.upper() for key in re.findall(r"(?i)\b[0-9a-f]{40}\b", match.group(1))))


def http_json(url: str) -> Mapping[str, object]:
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "rdp-session-manager-installer"})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise InstallerError(f"Falha ao consultar GitHub ({url}): {exc}") from exc


def download(url: str, destination: Path, ui: UI, log: InstallLog, retries: int = 3) -> None:
    request = Request(url, headers={"User-Agent": "rdp-session-manager-installer"})
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            ui.info(f"Baixando {destination.name} · tentativa {attempt}/{retries}")
            with urlopen(request, timeout=30) as response, destination.open("wb") as output:
                total = int(response.headers.get("Content-Length", "0"))
                received = 0
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(bar_width=32, complete_style="bright_cyan", finished_style="green"),
                    TaskProgressColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    console=ui.console,
                    expand=True,
                ) as progress:
                    task = progress.add_task(destination.name, total=total or None)
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        output.write(chunk)
                        received += len(chunk)
                        progress.update(task, advance=len(chunk))
            log.write(f"download {url} -> {destination} ({destination.stat().st_size} bytes)")
            return
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            log.write(f"download failed attempt {attempt}: {exc}")
            if attempt < retries:
                time.sleep(attempt * 2)
    raise InstallerError(f"Não foi possível baixar {url}: {last_error}. Log: {log.path}")


class Installer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.ui = UI(args.verbose, args.dry_run)
        self.ui.info("Preparando o assistente…")
        self.askpass = self._configure_graphical_auth()
        self.log = InstallLog()
        self.runner = Runner(self.ui, self.log, args.dry_run)
        self.distro = detect_distro(Path(args.os_release)) if args.os_release else detect_distro()
        self.ui.success(f"Sistema detectado: {self.distro.name}")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="rdpsm-install-"))
        self.release: Optional[Mapping[str, object]] = None

    def _configure_graphical_auth(self) -> Optional[str]:
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return None
        askpass = next(
            (path for name in ("ksshaskpass", "ssh-askpass", "lxqt-openssh-askpass") if (path := shutil.which(name))),
            None,
        )
        if askpass:
            os.environ["SUDO_ASKPASS"] = askpass
            os.environ["SUDO_ASKPASS_REQUIRE"] = "force"
        return askpass

    def close(self) -> None:
        self.ui.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if not self.log.handle.closed:
            self.log.close()

    def validate_version(self) -> None:
        if self.distro.family == "debian" and self.distro.identifier == "ubuntu":
            match = re.match(r"^(\d+)\.(\d+)", self.distro.version)
            if match and (int(match.group(1)), int(match.group(2))) < SUPPORTED_UBUNTU:
                raise InstallerError("Ubuntu 22.04 ou superior é necessário.")
        if self.distro.family == "debian" and self.distro.identifier == "debian":
            match = re.match(r"^(\d+)", self.distro.version)
            if match and int(match.group(1)) < SUPPORTED_DEBIAN:
                raise InstallerError("Debian 12 ou superior é necessário.")
        if platform.machine() not in {"x86_64", "amd64", "aarch64", "arm64"}:
            raise InstallerError(f"Arquitetura não suportada: {platform.machine()}")

    def release_info(self) -> Mapping[str, object]:
        if self.release is not None:
            return self.release
        if self.args.local:
            self.release = {"tag_name": "código local", "assets": [], "prerelease": False, "draft": False}
            return self.release
        if self.args.dry_run:
            self.release = {"tag_name": self.args.release or "latest-stable", "assets": [], "prerelease": False, "draft": False}
            return self.release
        if self.args.release:
            tag = self.args.release if self.args.release.startswith("v") else f"v{self.args.release}"
            endpoint = f"{API_BASE}/releases/tags/{tag}"
        else:
            endpoint = f"{API_BASE}/releases/latest"
        with self.ui.running("Consultando a release estável no GitHub…"):
            self.release = http_json(endpoint)
        if bool(self.release.get("prerelease")) or bool(self.release.get("draft")):
            raise InstallerError("A release selecionada é beta ou draft; selecione uma release estável.")
        return self.release

    def choose_components(self) -> None:
        """Resolve interactive optional-component choices before the plan."""
        if self.args.yes:
            if self.args.without_xrdp is None:
                self.args.without_xrdp = False
            if self.args.with_wine is None:
                self.args.with_wine = False
            return

        self.ui.console.print(
            Panel(
                Text(
                    "Escolha agora o que deve ser preparado. Essas opções poderão "
                    "ser revisadas no resumo antes da autenticação.",
                    style="white",
                ),
                title="[bold bright_cyan]Componentes da instalação[/]",
                border_style="cyan",
            )
        )
        if self.args.without_xrdp is None:
            install_xrdp = self.ui.component_prompt(
                "Servidor xrdp",
                "Necessário para receber conexões de Área de Trabalho Remota neste computador.",
                default=True,
            )
            self.args.without_xrdp = not install_xrdp
        if self.args.with_wine is None:
            self.args.with_wine = self.ui.component_prompt(
                "WineGE RemoteApp",
                "Adiciona as bibliotecas para executar aplicativos Windows nas sessões RDP. "
                "Pode aumentar significativamente o tempo e o tamanho da instalação.",
                default=False,
            )

    def asset_url(self, name: str) -> str:
        release = self.release_info()
        assets = release.get("assets", [])
        for asset in assets if isinstance(assets, list) else []:
            if isinstance(asset, dict) and asset.get("name") == name:
                url = asset.get("browser_download_url")
                if isinstance(url, str):
                    return url
        tag = release.get("tag_name")
        if isinstance(tag, str):
            return f"{DOWNLOAD_BASE}/download/{tag}/{name}"
        raise InstallerError(f"Asset não encontrado na release: {name}")

    def package_names(self) -> list[str]:
        if self.distro.family == "debian":
            packages = [
                "python3", "python3-gi", "python3-gi-cairo", "python3-psutil",
                "gir1.2-gtk-4.0", "gir1.2-adw-1", "libadwaita-1-0", "polkitd",
            ]
            if not self.args.without_xrdp:
                packages += ["xrdp", "xorgxrdp", "xorg", "x11-xserver-utils", "xauth", "openbox", "dbus-x11", "zenity"]
            if self.args.with_wine:
                packages += ["wine", "wine64", "wine32", "winetricks", "cabextract", "p7zip-full", "unzip", "curl", "wget"]
            return packages
        packages = ["python", "python-gobject", "python-cairo", "python-psutil", "gtk4", "libadwaita", "polkit"]
        if not self.args.without_xrdp:
            packages += ["xorg-server", "xorg-xinit", "xorg-xrandr", "xorg-xauth", "openbox", "dbus", "zenity"]
        if self.args.with_wine:
            packages += [
                "wine", "wine-mono", "wine-gecko", "winetricks",
                "lib32-gnutls", "lib32-libxinerama", "lib32-libpulse",
                "lib32-alsa-lib", "lib32-mesa", "vulkan-icd-loader",
                "lib32-vulkan-icd-loader", "cabextract", "7zip", "unzip",
                "curl", "wget", "tar",
            ]
        return packages

    def show_plan(self, app_asset: str) -> None:
        rows = [
            ("Sistema", f"{self.distro.name} · família {self.distro.family}"),
            ("Release", str(self.release_info().get("tag_name", "latest"))),
            ("Aplicação", app_asset),
            ("Servidor RDP", "Não instalar" if self.args.without_xrdp else "Instalar e ativar xrdp"),
            (
                "Origem do xrdp",
                "AUR oficial · PKGBUILDs compilados localmente"
                if self.distro.family == "arch" and not self.args.without_xrdp
                else "Repositórios oficiais",
            ),
            ("WineGE", "Instalar dependências opcionais" if self.args.with_wine else "Não instalar"),
            (
                "Repositório multilib",
                "Ativar automaticamente, se necessário" if self.args.with_wine else "Sem alterações",
            ),
            ("Log", str(self.log.path)),
        ]
        self.ui.show_plan(rows, self.package_names())
        if self.args.dry_run:
            self.ui.warning("Simulação concluída. Nenhum arquivo, pacote ou serviço foi alterado.")
            return
        if self.args.yes:
            return
        if not self.ui.confirm("[bold]Autorizar e iniciar todas as ações exibidas?[/]"):
            raise InstallerError("Instalação cancelada pelo usuário.")

    def preflight(self) -> None:
        self.ui.info("Verificando sistema, permissões e gerenciador de pacotes…")
        self.validate_version()
        if not self.args.dry_run and not command_exists("sudo") and os.geteuid() != 0:
            raise InstallerError("sudo não está disponível; execute como root ou instale sudo.")
        if self.distro.family == "debian" and not command_exists("apt-get"):
            raise InstallerError("apt-get não encontrado.")
        if self.distro.family == "arch" and not command_exists("pacman"):
            raise InstallerError("pacman não encontrado.")
        lock_paths = (
            (Path("/var/lib/dpkg/lock-frontend"), Path("/var/lib/apt/lists/lock"))
            if self.distro.family == "debian"
            else (Path("/var/lib/pacman/db.lck"),)
        )
        if not self.args.dry_run:
            locked = package_lock_held(lock_paths)
            if locked:
                raise InstallerError(f"O gerenciador de pacotes está ocupado ({locked}). Feche-o e tente novamente.")
        self.ui.success("Pré-verificações concluídas.")

    def privilege(self) -> list[str]:
        if os.geteuid() == 0:
            return []
        return ["sudo", "-A"] if self.askpass else ["sudo"]

    def install_debian(self, app_path: Path) -> None:
        prefix = self.privilege()
        self.ui.stage(3, 5, "Atualizando índices e instalando dependências Debian/Ubuntu")
        self.runner.run(prefix + ["apt-get", "update"], timeout=900)
        self.runner.run(prefix + ["apt-get", "install", "-y", "--no-install-recommends", *self.package_names(), str(app_path)], timeout=1800)
        if not self.args.without_xrdp:
            self.enable_service("xrdp")

    def aur_helper(self) -> Optional[str]:
        return next((name for name in ("paru", "yay") if command_exists(name)), None)

    def ensure_arch_multilib(self) -> None:
        if not self.args.with_wine:
            return
        pacman_conf = Path("/etc/pacman.conf")
        try:
            current = pacman_conf.read_text(encoding="utf-8")
        except OSError as exc:
            raise InstallerError(f"Não foi possível ler {pacman_conf}: {exc}") from exc
        updated = enable_multilib_config(current)
        if updated == current:
            return

        self.ui.warning(
            "O Wine no Arch precisa das bibliotecas de 32 bits do repositório oficial multilib. "
            "O instalador ativará [multilib] em /etc/pacman.conf e manterá uma cópia de segurança "
            "em /etc/pacman.conf.rdpsm.bak."
        )

        generated = self.temp_dir / "pacman.conf"
        generated.write_text(updated, encoding="utf-8")
        prefix = self.privilege()
        backup = Path("/etc/pacman.conf.rdpsm.bak")
        if not backup.exists():
            self.runner.run(
                prefix + ["cp", "--preserve=mode,ownership,timestamps", str(pacman_conf), str(backup)],
                timeout=30,
            )
        self.runner.run(
            prefix + ["install", "-o", "root", "-g", "root", "-m", "644", str(generated), str(pacman_conf)],
            timeout=30,
        )
        self.ui.success("Repositório multilib ativado.")

    def import_pkgbuild_keys(self, pkgbuild: Path) -> None:
        try:
            keys = pkgbuild_pgp_keys(pkgbuild.read_text(encoding="utf-8"))
        except OSError as exc:
            raise InstallerError(f"Não foi possível inspecionar {pkgbuild}: {exc}") from exc
        for fingerprint in keys:
            present = self.runner.run(
                ["gpg", "--batch", "--list-keys", fingerprint],
                timeout=30,
                check=False,
            )
            if present.returncode == 0:
                continue
            self.ui.info(f"Importando chave PGP declarada pelo PKGBUILD: {fingerprint}")
            for server in ("hkps://keyserver.ubuntu.com", "hkps://keys.openpgp.org"):
                result = self.runner.run(
                    ["gpg", "--batch", "--keyserver", server, "--recv-keys", fingerprint],
                    timeout=180,
                    check=False,
                )
                if result.returncode == 0:
                    break
            else:
                raise InstallerError(
                    f"Não foi possível importar a chave PGP {fingerprint} exigida por {pkgbuild}. "
                    f"Consulte o log: {self.log.path}"
                )

    def install_arch_xrdp(self) -> None:
        if self.args.without_xrdp:
            return
        helper = self.aur_helper()
        self.ui.warning(
            "No Arch, xrdp e xorgxrdp são compilados a partir do AUR. "
            "Os PKGBUILDs serão baixados, validados e compilados no seu usuário."
        )
        if helper:
            if helper == "yay":
                command = [
                    helper, "-S", "--needed", "--noconfirm",
                    "--answerclean", "None", "--answerdiff", "None",
                    "--noremovemake", "--pgpfetch", "xrdp", "xorgxrdp",
                ]
            else:
                command = [
                    helper, "-S", "--needed", "--noconfirm", "--skipreview",
                    "xrdp", "xorgxrdp",
                ]
            self.runner.run(command, timeout=2400)
            return
        if os.geteuid() == 0:
            raise InstallerError("AUR fallback precisa ser executado por usuário comum, não como root.")
        self.ui.warning("yay/paru não encontrado. Serão compilados PKGBUILDs oficiais do AUR.")
        self.runner.run(
            self.privilege() + ["pacman", "-S", "--needed", "--noconfirm", "git", "base-devel", "gnupg"],
            timeout=1800,
        )
        for package in ("xrdp", "xorgxrdp"):
            destination = self.temp_dir / package
            self.runner.run(["git", "clone", "--depth", "1", f"https://aur.archlinux.org/{package}.git", str(destination)], timeout=300)
            self.import_pkgbuild_keys(destination / "PKGBUILD")
            self.runner.run(
                ["makepkg", "--syncdeps", "--noconfirm", "--needed"],
                cwd=destination,
                timeout=2400,
            )
            package_list = self.runner.run(["makepkg", "--packagelist"], cwd=destination, timeout=30)
            built_packages = [
                Path(line.strip())
                for line in package_list.stdout.splitlines()
                if line.strip().endswith((".pkg.tar.zst", ".pkg.tar.xz", ".pkg.tar.gz"))
            ]
            if not built_packages:
                raise InstallerError(f"makepkg não informou o pacote gerado para {package}. Log: {self.log.path}")
            self.runner.run(
                self.privilege() + ["pacman", "-U", "--needed", "--noconfirm", *(str(path) for path in built_packages)],
                timeout=900,
            )

    def install_arch(self, app_path: Path) -> None:
        prefix = self.privilege()
        self.ui.stage(3, 5, "Atualizando Arch e instalando dependências")
        self.ensure_arch_multilib()
        self.runner.run(prefix + ["pacman", "-Syu", "--needed", "--noconfirm", *self.package_names()], timeout=1800)
        self.install_arch_xrdp()
        self.runner.run(prefix + ["pacman", "-U", "--noconfirm", str(app_path)], timeout=900)
        if not self.args.without_xrdp:
            self.enable_service("xrdp")

    def enable_service(self, name: str) -> None:
        prefix = self.privilege()
        self.ui.stage(4, 5, f"Ativando serviço {name}")
        self.runner.run(prefix + ["systemctl", "enable", "--now", name], timeout=60, check=False)
        if not self.args.dry_run and shutil.which("systemctl") and subprocess.run(["systemctl", "is-active", "--quiet", name]).returncode != 0:
            self.ui.warning(f"{name} não ficou ativo; consulte: journalctl -u {name}")

    def run(self) -> int:
        app_asset = APP_DEB if self.distro.family == "debian" else APP_ARCH
        try:
            self.preflight()
            self.choose_components()
            self.show_plan(app_asset)
            if self.args.dry_run:
                self.ui.complete("Simulação concluída")
                return 0
            # Do not start Rich's live progress display before interactive
            # prompts: it can redraw over the final confirmation and make the
            # installer look frozen at 0%.
            self.ui.stage(1, 5, "Plano aprovado")
            if self.args.local:
                app_path = Path(self.args.package_dir).expanduser().resolve() / app_asset
                self.ui.stage(2, 5, "Validando o pacote gerado localmente")
                if not app_path.is_file():
                    raise InstallerError(
                        f"Pacote local não encontrado: {app_path}\n"
                        "Gere os pacotes primeiro com: ./installer/build_packages.sh"
                    )
                actual = sha256(app_path)
                self.log.write(f"local package {app_path} sha256={actual}")
                self.ui.success(f"Pacote local encontrado e SHA-256 calculado: {actual}")
            else:
                app_path = self.temp_dir / app_asset
                checksums_path = self.temp_dir / "SHA256SUMS"
                self.ui.stage(2, 5, "Baixando e validando artefatos da release")
                download(self.asset_url(app_asset), app_path, self.ui, self.log)
                download(self.asset_url("SHA256SUMS"), checksums_path, self.ui, self.log)
                checksums = parse_checksums(checksums_path.read_text(encoding="utf-8"))
                expected = checksums.get(app_asset)
                if not expected:
                    raise InstallerError(f"SHA256SUMS não contém {app_asset}.")
                actual = sha256(app_path)
                if actual.lower() != expected.lower():
                    raise InstallerError(f"Checksum inválido para {app_asset}. Log: {self.log.path}")
                self.ui.success(f"Checksum validado: {actual}")
            if self.distro.family == "debian":
                self.install_debian(app_path)
            else:
                self.install_arch(app_path)
            self.ui.stage(5, 5, "Verificando instalação")
            self.runner.run(["rdp-session-manager", "--help"], timeout=30, check=False)
            if not self.args.without_xrdp:
                self.ui.success("xrdp foi instalado e configurado.")
            self.ui.complete()
            self.ui.console.print(
                Panel(
                    Text.assemble(
                        ("RDP Session Manager instalado com sucesso!\n\n", "bold green"),
                        ("Para abrir a aplicação:\n", "white"),
                        ("rdp-session-manager", "bold bright_cyan"),
                    ),
                    title="[bold green]Tudo pronto[/]",
                    border_style="green",
                    padding=(1, 3),
                )
            )
            self.ui.info(f"Log completo: {self.log.path}")
            return 0
        except (InstallerError, KeyboardInterrupt) as exc:
            self.ui.error(str(exc))
            self.ui.error(f"Log completo: {self.log.path}")
            return 130 if isinstance(exc, KeyboardInterrupt) else 1
        finally:
            self.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Instalador transparente do RDP Session Manager")
    result.add_argument("--yes", action="store_true", help="não solicitar confirmações")
    result.add_argument("--with-wine", action="store_true", default=None, help="instalar dependências opcionais do WineGE")
    result.add_argument("--without-xrdp", action="store_true", default=None, help="não instalar nem ativar xrdp")
    result.add_argument("--release", help="fixar release, por exemplo v0.4.0")
    result.add_argument("--local", action="store_true", help="instalar o pacote gerado neste clone")
    result.add_argument("--package-dir", default="release", help="diretório dos pacotes para --local")
    result.add_argument("--dry-run", action="store_true", help="mostrar o plano sem alterar o sistema")
    result.add_argument("--verbose", action="store_true", help="mostrar toda a saída dos comandos")
    result.add_argument("--os-release", help=argparse.SUPPRESS)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    installer: Optional[Installer] = None
    try:
        installer = Installer(args)
        return installer.run()
    except InstallerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if installer:
            installer.close()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
