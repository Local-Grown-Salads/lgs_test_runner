"""
Repo Manager - Clone, cache, and import functions.

Each worksheet maps to a repo/module. Functions are imported dynamically at runtime.
Supports fixture pattern for class-based SDKs.
"""

import importlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


@dataclass
class TestContext:
    """Context for a single test invocation."""

    func: Callable[..., Any]
    fixture: Any | None = None
    teardown_fn: Callable[[Any], None] | None = None

    def teardown(self) -> None:
        """Call teardown if configured."""
        if self.fixture is not None and self.teardown_fn is not None:
            self.teardown_fn(self.fixture)


class RepoManager:
    """Manages cloning, caching, and importing functions."""

    def __init__(self, config_path: str = "repos.json", cache_dir: str = "repos"):
        self.config_path = Path(config_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._modules: dict[str, ModuleType] = {}
        self._config: dict[str, dict[str, Any]] | None = None

    @property
    def config(self) -> dict[str, dict[str, Any]]:
        """Load and cache the repos config.

        Config format:
        {
            "sheet_name": {
                "repo": "git@github.com:org/repo.git",
                "parent_module": "lgs_agronomist_sdk",
                "fixtures": "Agronomist SDK/fixtures.py"
            }
        }

        The fixtures file should export:
        - create() -> fixture instance
        - teardown(fixture) -> cleanup
        """
        if self._config is None:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            with open(self.config_path) as f:
                self._config = json.load(f)
        return self._config

    def _repo_name_from_url(self, repo_url: str) -> str:
        """Extract repo name from URL."""
        # Handle both HTTPS and SSH URLs
        # https://github.com/org/repo.git -> repo
        # git@github.com:org/repo.git -> repo
        name = repo_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name

    def _repo_path(self, sheet_name: str) -> Path:
        """Get the local path for a repo."""
        repo_url = self.config[sheet_name]["repo"]
        repo_name = self._repo_name_from_url(repo_url)
        return self.cache_dir / repo_name

    def _clone_repo(self, repo_url: str, repo_path: Path) -> None:
        """Clone a repo with depth 1."""
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
            check=True,
            capture_output=True,
        )

    def _pull_repo(self, repo_path: Path) -> None:
        """Pull latest changes for a cached repo."""
        subprocess.run(
            ["git", "pull"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    def _setup_venv(self, repo_path: Path) -> Path:
        """Create isolated venv for a repo. Returns venv path."""
        venv_path = repo_path / ".venv"
        if not venv_path.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True,
            )
        return venv_path

    def _get_venv_python(self, venv_path: Path) -> str:
        """Get the python executable path for a venv."""
        if sys.platform == "win32":
            return str(venv_path / "Scripts" / "python.exe")
        return str(venv_path / "bin" / "python")

    def _get_venv_site_packages(self, venv_path: Path) -> Path:
        """Get the site-packages path for a venv."""
        if sys.platform == "win32":
            return venv_path / "Lib" / "site-packages"
        # Find the python version directory
        lib_path = venv_path / "lib"
        if lib_path.exists():
            for entry in lib_path.iterdir():
                if entry.name.startswith("python"):
                    return entry / "site-packages"
        raise RuntimeError(f"Could not find site-packages in {venv_path}")

    def _install_deps(self, repo_path: Path, venv_path: Path) -> None:
        """Install dependencies into the repo's venv."""
        python = self._get_venv_python(venv_path)

        # Try pyproject.toml / setup.py first (editable install)
        if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
            subprocess.run(
                [python, "-m", "pip", "install", "-e", str(repo_path), "-q"],
                check=True,
                capture_output=True,
            )
        # Fall back to requirements.txt
        elif (repo_path / "requirements.txt").exists():
            subprocess.run(
                [python, "-m", "pip", "install", "-r", str(repo_path / "requirements.txt"), "-q"],
                check=True,
                capture_output=True,
            )

    def _import_module(self, repo_path: Path, parent_module: str, venv_path: Path) -> ModuleType:
        """Import a module from a repo, using its isolated venv."""
        site_packages = self._get_venv_site_packages(venv_path)

        # Add paths for import
        original_path = sys.path.copy()
        sys.path.insert(0, str(site_packages))
        sys.path.insert(0, str(repo_path))

        try:
            # Use standard import for installed packages
            module = importlib.import_module(parent_module)
            return module
        finally:
            # Restore original sys.path
            sys.path = original_path

    def _load_fixture_module(self, fixtures_path: str) -> ModuleType:
        """Load a fixtures.py module from a file path."""
        path = Path(fixtures_path)
        if not path.exists():
            raise FileNotFoundError(f"Fixtures file not found: {path}")

        module_name = f"fixtures_{path.stem}_{id(path)}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load fixture module: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _create_fixture(
        self, sheet_name: str, venv_path: Path, repo_path: Path
    ) -> tuple[Any | None, Callable[[Any], None] | None]:
        """Create a fresh fixture instance for a sheet.

        Returns (instance, teardown_fn) by calling the fixtures module's create() function.
        """
        repo_config = self.config[sheet_name]
        fixtures_path = repo_config.get("fixtures")

        if not fixtures_path:
            return None, None

        # Add repo's venv to path so fixture can import the SDK
        site_packages = self._get_venv_site_packages(venv_path)
        original_path = sys.path.copy()
        sys.path.insert(0, str(site_packages))
        sys.path.insert(0, str(repo_path))

        try:
            fixture_module = self._load_fixture_module(fixtures_path)

            if not hasattr(fixture_module, "create"):
                raise AttributeError(f"Fixtures module missing 'create' function: {fixtures_path}")

            instance = fixture_module.create()
            teardown_fn = getattr(fixture_module, "teardown", None)

            return instance, teardown_fn
        finally:
            sys.path = original_path

    def setup_repo(self, sheet_name: str) -> tuple[ModuleType, Path, Path]:
        """Clone/pull repo, install deps, return (module, venv_path, repo_path)."""
        if sheet_name not in self.config:
            raise ValueError(f"No repo configured for worksheet: {sheet_name}")

        repo_config = self.config[sheet_name]
        repo_url = repo_config["repo"]
        parent_module = repo_config["parent_module"]
        repo_path = self._repo_path(sheet_name)

        # Clone or pull
        if repo_path.exists():
            self._pull_repo(repo_path)
        else:
            self._clone_repo(repo_url, repo_path)

        # Setup venv and install deps
        venv_path = self._setup_venv(repo_path)
        self._install_deps(repo_path, venv_path)

        # Import and cache module (module caching is fine, just not fixtures)
        if sheet_name not in self._modules:
            module = self._import_module(repo_path, parent_module, venv_path)
            self._modules[sheet_name] = module
        else:
            module = self._modules[sheet_name]

        return module, venv_path, repo_path

    def _resolve_dotted_attr(self, obj: Any, path: str) -> Any:
        """Resolve a dotted attribute path like 'assembly.get_product_by'."""
        for part in path.split("."):
            if not hasattr(obj, part):
                raise AttributeError(f"'{type(obj).__name__}' has no attribute '{part}'")
            obj = getattr(obj, part)
        return obj

    def get_function(self, sheet_name: str, func_name: str) -> TestContext:
        """Get a function from a repo's module or a fresh fixture instance.

        Supports dotted paths like 'assembly.get_product_by' for nested attributes.
        Returns TestContext with the callable and optional fixture for teardown.
        """
        module, venv_path, repo_path = self.setup_repo(sheet_name)

        # Create fresh fixture for this test
        fixture, teardown_fn = self._create_fixture(sheet_name, venv_path, repo_path)

        # If fixture exists, resolve method from fixture instance
        if fixture is not None:
            method = self._resolve_dotted_attr(fixture, func_name)
            if not callable(method):
                raise TypeError(f"'{func_name}' is not callable")
            return TestContext(func=method, fixture=fixture, teardown_fn=teardown_fn)

        # Otherwise, resolve from module
        func = self._resolve_dotted_attr(module, func_name)
        if not callable(func):
            raise TypeError(f"'{func_name}' is not callable")

        return TestContext(func=func)

    def refresh_all(self) -> None:
        """Pull latest for all configured repos."""
        for sheet_name in self.config:
            repo_path = self._repo_path(sheet_name)
            if repo_path.exists():
                self._pull_repo(repo_path)
        # Clear module cache to force reimport
        self._modules.clear()
