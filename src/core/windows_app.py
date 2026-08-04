#!/usr/bin/env python3
"""Lifecycle management for Windows applications exposed through RDP."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
from urllib.request import Request, urlopen


SCHEMA_VERSION = 1
VALID_STATES = {
    "staging",
    "prefix_ready",
    "installing",
    "awaiting_assisted_install",
    "discovering",
    "selection_required",
    "validating",
    "awaiting_rdp_validation",
    "ready",
    "failed",
}
WINDOWS_APP_ROOT = Path(".local/share/rdp-session-manager/windows-apps")


class WindowsAppError(RuntimeError):
    """An expected and actionable Windows application error."""


def _atomic_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_app_id(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value).strip(".-")
    if not value:
        value = f"app-{uuid.uuid4().hex[:12]}"
    if len(value) > 64:
        value = value[:64].rstrip(".-")
    return value


@dataclass
class InstallRecipe:
    """Declarative and shell-free installation instructions."""

    recipe_id: str
    name: str
    installer_type: str = "exe"
    silent_args: List[str] = field(default_factory=list)
    success_codes: List[int] = field(default_factory=lambda: [0, 1641, 3010])
    timeout: int = 900
    executable_patterns: List[str] = field(default_factory=list)
    winetricks: List[str] = field(default_factory=list)
    source_url: str = ""
    source_sha256: str = ""
    source_filename: str = ""
    runner: str = "umu-proton"
    architecture: str = "win64"
    app_args: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "InstallRecipe":
        if int(data.get("schema_version", SCHEMA_VERSION)) != SCHEMA_VERSION:
            raise WindowsAppError("Unsupported recipe schema version")
        installer = data.get("installer", {})
        source = data.get("source", {})
        executable = data.get("executable", {})
        runtime = data.get("runtime", {})
        recipe = cls(
            recipe_id=safe_app_id(str(data.get("id", ""))),
            name=str(data.get("name", "")).strip(),
            installer_type=str(installer.get("type", "exe")).lower(),
            silent_args=[str(item) for item in installer.get("silent_args", [])],
            success_codes=[int(item) for item in installer.get("success_codes", [0, 1641, 3010])],
            timeout=int(installer.get("timeout", 900)),
            executable_patterns=[str(item) for item in executable.get("patterns", [])],
            winetricks=[str(item) for item in data.get("winetricks", [])],
            source_url=str(source.get("url", "")),
            source_sha256=str(source.get("sha256", "")).lower(),
            source_filename=str(source.get("filename", "")),
            runner=str(runtime.get("runner", "umu-proton")),
            architecture=str(runtime.get("architecture", "win64")),
            app_args=[str(item) for item in executable.get("args", [])],
        )
        recipe.validate()
        return recipe

    @classmethod
    def load(cls, path: Path) -> "InstallRecipe":
        with path.open("r", encoding="utf-8") as stream:
            return cls.from_dict(json.load(stream))

    def validate(self) -> None:
        if not self.name:
            raise WindowsAppError("Recipe name cannot be empty")
        if self.installer_type not in {"exe", "msi", "portable"}:
            raise WindowsAppError(f"Unsupported installer type: {self.installer_type}")
        if self.runner not in {"umu-proton", "winege-legacy"}:
            raise WindowsAppError(f"Unsupported runner: {self.runner}")
        if self.architecture not in {"win32", "win64"}:
            raise WindowsAppError(f"Unsupported prefix architecture: {self.architecture}")
        if self.timeout < 1 or self.timeout > 86400:
            raise WindowsAppError("Recipe timeout must be between 1 and 86400 seconds")
        if self.source_url and not self.source_url.startswith("https://"):
            raise WindowsAppError("Catalog downloads require HTTPS")
        if self.source_url and not re.fullmatch(r"[a-f0-9]{64}", self.source_sha256):
            raise WindowsAppError("Catalog downloads require a SHA-256 checksum")
        for value in self.silent_args + self.app_args + self.winetricks:
            if "\x00" in value or "\n" in value:
                raise WindowsAppError("Recipe arguments cannot contain NUL or newline characters")

    def to_dict(self) -> Dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.recipe_id,
            "name": self.name,
            "source": {
                "url": self.source_url,
                "sha256": self.source_sha256,
                "filename": self.source_filename,
            },
            "installer": {
                "type": self.installer_type,
                "silent_args": self.silent_args,
                "success_codes": self.success_codes,
                "timeout": self.timeout,
            },
            "runtime": {"runner": self.runner, "architecture": self.architecture},
            "winetricks": self.winetricks,
            "executable": {"patterns": self.executable_patterns, "args": self.app_args},
        }


class RecipeCatalog:
    def __init__(self, directories: Optional[Iterable[Path]] = None):
        project_data = Path(__file__).resolve().parents[2] / "data" / "windows-app-recipes"
        system_data = Path("/usr/share/rdp-session-manager/windows-app-recipes")
        self.directories = list(
            directories if directories is not None else (project_data, system_data)
        )

    def list(self) -> List[InstallRecipe]:
        recipes: Dict[str, InstallRecipe] = {}
        for directory in self.directories:
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                recipe = InstallRecipe.load(path)
                recipes[recipe.recipe_id] = recipe
        return sorted(recipes.values(), key=lambda item: item.name.lower())

    def get(self, recipe_id_or_path: str) -> InstallRecipe:
        path = Path(recipe_id_or_path)
        if path.is_file():
            return InstallRecipe.load(path)
        for recipe in self.list():
            if recipe.recipe_id == recipe_id_or_path:
                return recipe
        raise WindowsAppError(f"Recipe not found: {recipe_id_or_path}")


class WindowsAppManager:
    """Manages one isolated compatibility prefix per Windows application."""

    def __init__(self, home_dir: Path, catalog: Optional[RecipeCatalog] = None):
        self.home_dir = Path(home_dir)
        self.root = self.home_dir / WINDOWS_APP_ROOT
        self.catalog = catalog or RecipeCatalog()

    def _chown_tree(self, path: Path) -> None:
        if os.geteuid() != 0 or not path.exists():
            return
        owner = self.home_dir.stat()
        for item in [path, *path.rglob("*")]:
            os.chown(item, owner.st_uid, owner.st_gid, follow_symlinks=False)

    def _run(self, command: Sequence[str], **kwargs) -> subprocess.CompletedProcess:
        if os.geteuid() == 0:
            owner = self.home_dir.stat()

            def demote() -> None:
                os.setgroups([])
                os.setgid(owner.st_gid)
                os.setuid(owner.st_uid)

            kwargs["preexec_fn"] = demote
        return subprocess.run(command, **kwargs)

    def _popen(self, command: Sequence[str], **kwargs) -> subprocess.Popen:
        if os.geteuid() == 0:
            owner = self.home_dir.stat()

            def demote() -> None:
                os.setgroups([])
                os.setgid(owner.st_gid)
                os.setuid(owner.st_uid)

            kwargs["preexec_fn"] = demote
        return subprocess.Popen(command, **kwargs)

    def app_dir(self, app_id: str) -> Path:
        normalized = safe_app_id(app_id)
        if normalized != app_id:
            raise WindowsAppError(f"Invalid app id: {app_id}")
        return self.root / normalized

    def manifest_path(self, app_id: str) -> Path:
        return self.app_dir(app_id) / "manifest.json"

    def state_path(self, app_id: str) -> Path:
        return self.app_dir(app_id) / "state.json"

    def load_manifest(self, app_id: str) -> Dict:
        with self.manifest_path(app_id).open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def load_state(self, app_id: str) -> Dict:
        path = self.state_path(app_id)
        if not path.exists():
            return {"state": "failed", "message": "Application state is missing"}
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def list_apps(self) -> List[Tuple[Dict, Dict]]:
        result = []
        if not self.root.is_dir():
            return result
        for manifest_path in sorted(self.root.glob("*/manifest.json")):
            app_id = manifest_path.parent.name
            try:
                result.append((self.load_manifest(app_id), self.load_state(app_id)))
            except (OSError, ValueError):
                continue
        return result

    def set_state(self, app_id: str, state: str, message: str = "", **details) -> Dict:
        if state not in VALID_STATES:
            raise WindowsAppError(f"Invalid application state: {state}")
        previous = self.load_state(app_id) if self.state_path(app_id).exists() else {}
        history = list(previous.get("history", []))
        event = {"state": state, "timestamp": int(time.time()), "message": message}
        history.append(event)
        data = {**event, "history": history[-100:], **details}
        _atomic_json(self.state_path(app_id), data)
        return data

    @contextmanager
    def lock(self, app_id: str) -> Iterator[None]:
        lock_path = self.app_dir(app_id) / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("w", encoding="utf-8") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise WindowsAppError(f"Another operation is active for {app_id}") from exc
            yield

    def _download(self, recipe: InstallRecipe, destination: Path) -> Path:
        filename = recipe.source_filename or Path(recipe.source_url).name or "installer.exe"
        target = destination / filename
        request = Request(recipe.source_url, headers={"User-Agent": "rdp-session-manager"})
        with urlopen(request, timeout=60) as response, target.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256_file(target) != recipe.source_sha256:
            target.unlink(missing_ok=True)
            raise WindowsAppError("Downloaded installer checksum does not match the recipe")
        return target

    def stage(
        self,
        recipe: InstallRecipe,
        source: Optional[Path] = None,
        app_id: Optional[str] = None,
        profile_id: str = "",
    ) -> str:
        app_id = safe_app_id(app_id or recipe.recipe_id)
        app_dir = self.app_dir(app_id)
        if self.manifest_path(app_id).exists():
            raise WindowsAppError(f"Application already exists: {app_id}")
        with self.lock(app_id):
            source_dir = app_dir / "source"
            prefix = app_dir / "prefix"
            logs = app_dir / "logs"
            artifacts = app_dir / "artifacts"
            for directory in (source_dir, prefix, logs, artifacts):
                directory.mkdir(parents=True, exist_ok=True)

            if source:
                source = Path(source).resolve()
                if not source.exists():
                    raise WindowsAppError(f"Source not found: {source}")
                target = source_dir / source.name
                if source.is_dir():
                    shutil.copytree(source, target)
                    staged_source = target
                    digest = ""
                else:
                    shutil.copy2(source, target)
                    staged_source = target
                    digest = sha256_file(target)
                    if recipe.source_sha256 and digest != recipe.source_sha256:
                        raise WindowsAppError("Local installer checksum does not match the recipe")
            elif recipe.source_url:
                staged_source = self._download(recipe, source_dir)
                digest = recipe.source_sha256
            else:
                raise WindowsAppError("A local source or a catalog URL is required")

            manifest = {
                "schema_version": SCHEMA_VERSION,
                "app_id": app_id,
                "profile_id": profile_id,
                "name": recipe.name,
                "created_at": int(time.time()),
                "source": {
                    "path": str(staged_source),
                    "sha256": digest,
                    "original": str(source) if source else recipe.source_url,
                },
                "recipe": recipe.to_dict(),
                "runtime": {
                    "runner": recipe.runner,
                    "architecture": recipe.architecture,
                },
                "prefix": str(prefix),
                "executable": "",
                "app_args": recipe.app_args,
            }
            _atomic_json(self.manifest_path(app_id), manifest)
            self.set_state(app_id, "staging", "Source staged and verified")
            self._chown_tree(app_dir)
        return app_id

    def resolve_runner(self, manifest: Dict) -> List[str]:
        runner = manifest["runtime"]["runner"]
        prefix = manifest["prefix"]
        if runner == "umu-proton":
            executable = shutil.which("umu-run")
            if not executable:
                raise WindowsAppError(
                    "umu-run is not installed; install UMU Launcher or use winege-legacy"
                )
            return [executable]
        config = self.home_dir / ".winege_config"
        if config.exists():
            values = {}
            for line in config.read_text(encoding="utf-8").splitlines():
                key, separator, value = line.partition("=")
                if separator:
                    values[key] = value
            wine_bin = values.get("WINE_BIN")
            if wine_bin and Path(wine_bin).is_file():
                return [wine_bin]
        executable = shutil.which("wine")
        if not executable:
            raise WindowsAppError("No WineGE legacy or system Wine executable was found")
        return [executable]

    def runner_environment(self, manifest: Dict) -> Dict[str, str]:
        environment = os.environ.copy()
        runtime_dir = self.app_dir(manifest["app_id"]) / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(runtime_dir, 0o700)
        self._chown_tree(runtime_dir)
        environment.update(
            {
                "HOME": str(self.home_dir),
                "WINEPREFIX": manifest["prefix"],
                "WINEARCH": manifest["runtime"].get("architecture", "win64"),
                "WINEDEBUG": environment.get("WINEDEBUG", "-all"),
                "XDG_RUNTIME_DIR": str(runtime_dir),
            }
        )
        if manifest["runtime"]["runner"] == "umu-proton":
            environment.setdefault("GAMEID", "umu-default")
            environment.setdefault("STORE", "none")
        return environment

    def create_prefix(self, app_id: str) -> None:
        manifest = self.load_manifest(app_id)
        prefix = Path(manifest["prefix"])
        if (prefix / "drive_c").is_dir():
            self.set_state(app_id, "prefix_ready", "Compatibility prefix already exists")
            return
        if manifest["runtime"]["runner"] == "umu-proton":
            # UMU/Proton owns prefix initialization and performs it atomically
            # on the first real target. Calling a host wineboot here would mix
            # two different runners in one prefix.
            prefix.mkdir(parents=True, exist_ok=True)
            self._chown_tree(self.app_dir(app_id))
            self.set_state(
                app_id,
                "prefix_ready",
                "UMU will initialize the prefix with the installer or application",
            )
            return
        runner = self.resolve_runner(manifest)
        env = self.runner_environment(manifest)
        self.set_state(app_id, "prefix_ready", "Creating compatibility prefix")
        command = runner + ["wineboot", "-u"]
        self._chown_tree(self.app_dir(app_id))
        result = self._run(command, env=env, capture_output=True, text=True, timeout=300)
        self._append_log(app_id, "prefix.log", command, result)
        if result.returncode != 0 or not (prefix / "drive_c").is_dir():
            self.set_state(app_id, "failed", "Failed to create compatibility prefix")
            raise WindowsAppError("Compatibility prefix initialization failed")
        self.set_state(app_id, "prefix_ready", "Compatibility prefix created")

    def _append_log(
        self, app_id: str, name: str, command: Sequence[str], result: subprocess.CompletedProcess
    ) -> None:
        log_path = self.app_dir(app_id) / "logs" / name
        with log_path.open("a", encoding="utf-8", errors="replace") as stream:
            stream.write(f"$ {json.dumps(list(command))}\n")
            stream.write(result.stdout or "")
            stream.write(result.stderr or "")
            stream.write(f"\n[exit={result.returncode}]\n")

    def inventory_executables(self, app_id: str) -> List[str]:
        manifest = self.load_manifest(app_id)
        app_dir = self.app_dir(app_id)
        roots = [Path(manifest["prefix"]) / "drive_c", app_dir / "source"]
        found = []
        for root in roots:
            if root.exists():
                found.extend(str(item) for item in root.rglob("*.exe") if item.is_file())
        return sorted(set(found))

    @staticmethod
    def _is_auxiliary(path: str) -> bool:
        lowered = path.lower().replace("\\", "/")
        name = Path(lowered).name
        ignored = (
            "unins",
            "uninst",
            "setup",
            "installer",
            "crashreport",
            "update",
            "helper",
            "gup.exe",
        )
        system_paths = (
            "/windows/",
            "/internet explorer/",
            "/windows media player/",
            "/windows nt/",
        )
        return any(token in name for token in ignored) or any(
            token in lowered for token in system_paths
        )

    def discover(self, app_id: str, before: Optional[Iterable[str]] = None) -> List[Dict]:
        manifest = self.load_manifest(app_id)
        before_set = set(before or [])
        patterns = manifest["recipe"]["executable"].get("patterns", [])
        candidates = []
        for executable in self.inventory_executables(app_id):
            if self._is_auxiliary(executable):
                continue
            score = 10
            reasons = []
            if executable not in before_set:
                score += 50
                reasons.append("created-by-installer")
            relative = executable.lower().replace("\\", "/")
            for pattern in patterns:
                if Path(executable).match(pattern) or relative.endswith(pattern.lower()):
                    score += 100
                    reasons.append("recipe-match")
                    break
            if "/program files" in relative:
                score += 20
                reasons.append("program-files")
            candidates.append({"path": executable, "score": score, "reasons": reasons})
        candidates.sort(key=lambda item: (-item["score"], item["path"].lower()))
        return candidates

    def select_executable(self, app_id: str, executable: str) -> None:
        manifest = self.load_manifest(app_id)
        path = Path(executable)
        allowed_roots = [Path(manifest["prefix"]).resolve(), (self.app_dir(app_id) / "source").resolve()]
        resolved = path.resolve()
        if not path.is_file() or not any(
            resolved == root or root in resolved.parents for root in allowed_roots
        ):
            raise WindowsAppError("Executable must exist inside the application source or prefix")
        manifest["executable"] = str(resolved)
        _atomic_json(self.manifest_path(app_id), manifest)
        self.set_state(app_id, "validating", "Executable selected", executable=str(resolved))

    def install(self, app_id: str, mode: str = "auto") -> Dict:
        if mode not in {"auto", "portable", "assisted"}:
            raise WindowsAppError(f"Unsupported installation mode: {mode}")
        with self.lock(app_id):
            manifest = self.load_manifest(app_id)
            recipe = InstallRecipe.from_dict(manifest["recipe"])
            self.create_prefix(app_id)
            self.apply_dependencies(app_id)
            source = Path(manifest["source"]["path"])
            before = self.inventory_executables(app_id)
            if mode == "assisted" or (
                mode == "auto" and recipe.installer_type == "exe" and not recipe.silent_args
            ):
                return self.set_state(
                    app_id,
                    "awaiting_assisted_install",
                    "Connect through RDP to complete the installer",
                    installer=str(source),
                    before=before,
                )
            if recipe.installer_type == "portable" or mode == "portable":
                candidates = self.discover(app_id, before=[])
            else:
                runner = self.resolve_runner(manifest)
                env = self.runner_environment(manifest)
                if recipe.installer_type == "msi":
                    command = runner + ["msiexec", "/i", str(source)] + recipe.silent_args
                else:
                    command = runner + [str(source)] + recipe.silent_args
                self.set_state(app_id, "installing", "Running unattended installer")
                self._chown_tree(self.app_dir(app_id))
                result = self._run(
                    command,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=recipe.timeout,
                )
                self._append_log(app_id, "install.log", command, result)
                if result.returncode not in recipe.success_codes:
                    self.set_state(
                        app_id,
                        "failed",
                        f"Installer exited with code {result.returncode}",
                    )
                    raise WindowsAppError(f"Installer failed with exit code {result.returncode}")
                candidates = self.discover(app_id, before)

            self.set_state(app_id, "discovering", "Searching for installed executables")
            if not candidates:
                return self.set_state(
                    app_id, "selection_required", "No application executable was found", candidates=[]
                )
            if len(candidates) > 1 and candidates[0]["score"] == candidates[1]["score"]:
                return self.set_state(
                    app_id,
                    "selection_required",
                    "Multiple application executables were found",
                    candidates=candidates,
                )
            self.select_executable(app_id, candidates[0]["path"])
            return self.load_state(app_id)

    def apply_dependencies(self, app_id: str) -> None:
        manifest = self.load_manifest(app_id)
        verbs = manifest["recipe"].get("winetricks", [])
        if not verbs:
            return
        winetricks = shutil.which("winetricks")
        if not winetricks:
            raise WindowsAppError("This recipe requires winetricks, but it is not installed")
        for verb in verbs:
            if not re.fullmatch(r"[a-zA-Z0-9_.+-]+", verb):
                raise WindowsAppError(f"Unsafe winetricks verb in recipe: {verb}")
        command = [winetricks, "-q", *verbs]
        result = self._run(
            command,
            env=self.runner_environment(manifest),
            capture_output=True,
            text=True,
            timeout=1800,
        )
        self._append_log(app_id, "winetricks.log", command, result)
        if result.returncode != 0:
            raise WindowsAppError(f"Winetricks failed with exit code {result.returncode}")

    def finalize_assisted(self, app_id: str) -> Dict:
        """Discover the final executable after an interactive installer exits."""
        with self.lock(app_id):
            state = self.load_state(app_id)
            before = state.get("before", [])
            self.set_state(app_id, "discovering", "Interactive installer finished")
            candidates = self.discover(app_id, before)
            if not candidates:
                return self.set_state(
                    app_id, "selection_required", "No application executable was found", candidates=[]
                )
            if len(candidates) > 1 and candidates[0]["score"] == candidates[1]["score"]:
                return self.set_state(
                    app_id,
                    "selection_required",
                    "Multiple application executables were found",
                    candidates=candidates,
                )
            self.select_executable(app_id, candidates[0]["path"])
            return self.load_state(app_id)

    def launch_command(self, app_id: str, extra_args: Sequence[str] = ()) -> Tuple[List[str], Dict]:
        manifest = self.load_manifest(app_id)
        executable = manifest.get("executable")
        if not executable or not Path(executable).is_file():
            raise WindowsAppError("The application executable has not been selected")
        command = self.resolve_runner(manifest) + [executable]
        command.extend(str(item) for item in manifest.get("app_args", []))
        command.extend(str(item) for item in extra_args)
        return command, self.runner_environment(manifest)

    def validate_local(self, app_id: str, grace_seconds: int = 5) -> Dict:
        """Smoke-test process startup; the real window is confirmed by the RDP launcher."""
        command, environment = self.launch_command(app_id)
        if not environment.get("DISPLAY"):
            xvfb_run = shutil.which("xvfb-run")
            if not xvfb_run:
                raise WindowsAppError(
                    "Local graphical validation requires DISPLAY or the xvfb-run command"
                )
            command = [xvfb_run, "-a", "--server-args=-screen 0 1280x720x24", *command]
        self.set_state(app_id, "validating", "Starting local compatibility smoke test")
        log_path = self.app_dir(app_id) / "logs" / "validation.log"
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            process = self._popen(command, env=environment, stdout=log, stderr=log)
            deadline = time.monotonic() + max(1, grace_seconds)
            while time.monotonic() < deadline:
                return_code = process.poll()
                if return_code is not None:
                    self.set_state(
                        app_id,
                        "failed",
                        f"Application exited during validation with code {return_code}",
                    )
                    raise WindowsAppError(
                        f"Application exited during validation with code {return_code}"
                    )
                time.sleep(0.25)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        return self.set_state(
            app_id,
            "awaiting_rdp_validation",
            "Local launch passed; connect through RDP to validate the graphical window",
            validation={"local_process": True, "timestamp": int(time.time())},
        )

    def remove(self, app_id: str) -> None:
        app_dir = self.app_dir(app_id)
        if not self.manifest_path(app_id).is_file():
            raise WindowsAppError(f"Application not found: {app_id}")
        shutil.rmtree(app_dir)

    def mark_rdp_ready(self, app_id: str, pid: int) -> None:
        self.set_state(
            app_id,
            "ready",
            "Application launched successfully through RDP",
            validation={"rdp": True, "pid": pid, "timestamp": int(time.time())},
        )

    def migrate_legacy(self, app_id: str, name: str, executable: Path, profile_id: str) -> str:
        legacy_prefix = self.home_dir / ".wine"
        if not legacy_prefix.is_dir():
            raise WindowsAppError("Legacy Wine prefix was not found")
        recipe = InstallRecipe(
            recipe_id=safe_app_id(app_id),
            name=name,
            installer_type="portable",
            runner="winege-legacy",
            executable_patterns=[Path(executable).name],
        )
        staged_id = self.stage(recipe, source=executable, app_id=app_id, profile_id=profile_id)
        target_prefix = self.app_dir(staged_id) / "prefix"
        shutil.rmtree(target_prefix)
        result = subprocess.run(
            ["cp", "-a", "--reflink=auto", f"{legacy_prefix}/.", str(target_prefix)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.set_state(staged_id, "failed", "Failed to clone legacy prefix")
            raise WindowsAppError(result.stderr.strip() or "Failed to clone legacy prefix")
        resolved_exe = Path(str(executable).replace(str(legacy_prefix), str(target_prefix), 1))
        if not resolved_exe.is_file():
            resolved_exe = self.app_dir(staged_id) / "source" / executable.name
        self.select_executable(staged_id, str(resolved_exe))
        self.set_state(staged_id, "awaiting_rdp_validation", "Legacy profile migrated")
        self._chown_tree(self.app_dir(staged_id))
        return staged_id
