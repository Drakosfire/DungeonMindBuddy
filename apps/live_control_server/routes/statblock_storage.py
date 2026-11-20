"""One persistent root for the statblock product lifecycle, independent of code."""
from pathlib import Path
from fastapi import HTTPException
from apps.live_control_server.config import ArtifactDataRootError, artifact_data_root


def statblock_data_root(code_root: Path) -> Path:
    try:
        return artifact_data_root(default=code_root)
    except ArtifactDataRootError as exc:
        raise HTTPException(status_code=503, detail="Statblock storage unavailable") from exc
