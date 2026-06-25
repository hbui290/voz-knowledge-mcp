import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class BrowserSpec:
    name: str
    env_name: str
    port: int
    mac_app_path: str

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


DEFAULT_BROWSER_SPECS = [
    BrowserSpec("chrome", "VOZ_CHROME_CDP_URL", 9223, "/Applications/Google Chrome.app"),
    BrowserSpec("brave", "VOZ_BRAVE_CDP_URL", 9222, "/Applications/Brave Browser.app"),
    BrowserSpec("edge", "VOZ_EDGE_CDP_URL", 9224, "/Applications/Microsoft Edge.app"),
    BrowserSpec("chromium", "VOZ_CHROMIUM_CDP_URL", 9225, "/Applications/Chromium.app"),
    BrowserSpec("arc", "VOZ_ARC_CDP_URL", 9226, "/Applications/Arc.app"),
    BrowserSpec("vivaldi", "VOZ_VIVALDI_CDP_URL", 9227, "/Applications/Vivaldi.app"),
    BrowserSpec("opera", "VOZ_OPERA_CDP_URL", 9228, "/Applications/Opera.app"),
    BrowserSpec("coccoc", "VOZ_COCCOC_CDP_URL", 9229, "/Applications/CocCoc.app"),
]


class BrowserCdpManager:
    def __init__(self, state_dir: Path, specs: Optional[List[BrowserSpec]] = None):
        self.state_dir = Path(state_dir)
        self.specs = specs or DEFAULT_BROWSER_SPECS

    def cdp_urls(self, auto_launch: bool = True) -> List[str]:
        ordered = []
        ordered.extend(self._split_env_urls(os.environ.get("VOZ_BROWSER_CDP_URLS")))
        for spec in self.specs:
            value = os.environ.get(spec.env_name)
            if value:
                ordered.append(value.strip())
        generic = os.environ.get("VOZ_BROWSER_CDP_URL")
        if generic:
            ordered.append(generic.strip())

        if auto_launch and self._auto_launch_enabled():
            for spec in self.specs:
                if self._is_installed(spec) and self._launch(spec):
                    ordered.append(spec.url)
                    time.sleep(float(os.environ.get("VOZ_BROWSER_CDP_LAUNCH_WAIT", "1.0")))
        return self._dedupe(ordered)

    def setup(self) -> Dict[str, object]:
        launched = []
        skipped = []
        for spec in self.specs:
            if not self._is_installed(spec):
                skipped.append({"browser": spec.name, "reason": "not installed"})
                continue
            ok = self._launch(spec)
            if ok:
                launched.append({"browser": spec.name, "url": spec.url, "port": spec.port})
            else:
                skipped.append({"browser": spec.name, "reason": "launch failed"})
        return {"urls": [item["url"] for item in launched], "launched": launched, "skipped": skipped}

    def _launch(self, spec: BrowserSpec) -> bool:
        if platform.system() != "Darwin":
            return False
        app_path = Path(spec.mac_app_path)
        if not app_path.exists():
            return False
        self.state_dir.mkdir(parents=True, exist_ok=True)
        user_data_dir = self.state_dir / "browser-profiles" / spec.name
        user_data_dir.mkdir(parents=True, exist_ok=True)
        args = [
            "open",
            "-na",
            str(app_path),
            "--args",
            f"--remote-debugging-port={spec.port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={user_data_dir}",
        ]
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            return False

    def _is_installed(self, spec: BrowserSpec) -> bool:
        if platform.system() == "Darwin":
            return Path(spec.mac_app_path).exists()
        return False

    def _auto_launch_enabled(self) -> bool:
        return os.environ.get("VOZ_AUTO_LAUNCH_BROWSERS", "1").lower() not in {"0", "false", "no", "off"}

    def _split_env_urls(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]

    def _dedupe(self, values: Iterable[str]) -> List[str]:
        seen = set()
        result = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result
