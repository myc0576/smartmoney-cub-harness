from __future__ import annotations

import os
import sysconfig
from pathlib import Path


def launcher_diagnostics(
    path_value: str | None = None,
    scripts_dir: str | Path | None = None,
    platform_name: str | None = None,
    pathext: str | None = None,
) -> dict[str, bool | int]:
    path_value = os.environ.get("PATH", "") if path_value is None else path_value
    scripts_path = Path(sysconfig.get_path("scripts") if scripts_dir is None else scripts_dir)
    platform_name = os.name if platform_name is None else platform_name
    if platform_name == "nt":
        raw_extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD") if pathext is None else pathext
        names = [f"smcub{extension.lower()}" for extension in raw_extensions.split(";") if extension]
    else:
        names = ["smcub"]

    launchers: list[Path] = []
    seen: set[str] = set()
    for entry in path_value.split(os.pathsep):
        if not entry:
            continue
        for name in names:
            candidate = Path(entry) / name
            if not candidate.is_file():
                continue
            identity = os.path.normcase(str(candidate.resolve()))
            if identity not in seen:
                seen.add(identity)
                launchers.append(candidate)

    current_scripts = os.path.normcase(str(scripts_path.resolve()))
    first_is_current = bool(launchers) and os.path.normcase(str(launchers[0].parent.resolve())) == current_scripts
    return {
        "launcher_found": bool(launchers),
        "launcher_count": len(launchers),
        "multiple_launchers": len(launchers) > 1,
        "resolved_to_current_environment": first_is_current,
    }
