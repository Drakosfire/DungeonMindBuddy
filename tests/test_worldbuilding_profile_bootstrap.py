"""The production adapter must register every admitted profile in a fresh process."""

import os
from pathlib import Path
import subprocess
import sys


def test_generationengine_adapter_registers_supported_profiles_without_test_imports():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-c', '''
from apps.live_control_server.services.worldbuilding_ge_execution import SUPPORTED_PROFILE_VERSIONS
from src.graph_memory.extraction.extraction_profile import require_admitted_profile
for version in sorted(SUPPORTED_PROFILE_VERSIONS):
    profile = require_admitted_profile(
        profile_id="worldbuilding_gazetteer_v1", profile_version=version,
        source_domain="worldbuilding", document_class="lore", session_id=None,
    )
    assert profile.qualified_id == "worldbuilding_gazetteer_v1@" + version
'''],
        cwd=root,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join([str(root), str(root / 'src'), os.environ.get('PYTHONPATH', '')])},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
