import sys
from pathlib import Path


def ensure_src_on_path() -> None:
    cwd = Path.cwd().resolve()
    candidates = [cwd, *cwd.parents]
    extra = [
        Path("/lakehouse/default/Files"),
        Path("/lakehouse/default/Files/repo"),
        Path("/lakehouse/default/Files/microsoft"),
    ]
    for base in candidates + extra:
        src = base / "src"
        if (src / "emt_pipeline").exists():
            src_s = str(src)
            if src_s not in sys.path:
                sys.path.insert(0, src_s)
            return
    raise RuntimeError(
        "Cannot locate src/emt_pipeline. Sync the repo into Fabric or place "
        "the repo so notebooks can see the src directory."
    )

