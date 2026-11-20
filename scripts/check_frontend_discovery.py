"""Compare the installed frontend runners' discovery with CI inventory."""

import json
import subprocess
from pathlib import Path

from ci_contract import ROOT, discover


def main() -> int:
    prefix = "apps/live-control-ui/"
    ui = ROOT / prefix
    candidates = {path.removeprefix(prefix) for path in discover(ROOT) if path.startswith(prefix)}
    vitest = json.loads(subprocess.check_output(
        ["node_modules/.bin/vitest", "list", "--filesOnly", "--json"], cwd=ui
    ))
    playwright = json.loads(subprocess.check_output(
        ["npm", "run", "--silent", "ui:visual", "--", "--list", "--reporter=json"], cwd=ui
    ))
    test_dir = Path(playwright["config"]["projects"][0]["testDir"])
    visual = {
        (test_dir / suite["file"]).relative_to(ui).as_posix()
        for suite in playwright["suites"]
    }
    comparisons = (
        ("Vitest", {p for p in candidates if not p.endswith(".pw.ts")},
         {Path(entry["file"]).relative_to(ui).as_posix() for entry in vitest}),
        ("Playwright visual", {p for p in candidates if Path(p).name == "ui-visual.pw.ts"}, visual),
    )
    failed = False
    for name, expected, selected in comparisons:
        if expected != selected:
            print(f"{name}: missing={sorted(expected - selected)}, extra={sorted(selected - expected)}")
            failed = True
        else:
            print(f"{name}: verified {len(selected)} selected files")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
