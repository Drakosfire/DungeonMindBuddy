"""Run the container-local Buddy liveness or readiness check."""

import argparse
from urllib.error import URLError
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", choices=("live", "ready"))
    parser.add_argument("timeout", type=float)
    args = parser.parse_args()
    try:
        with urlopen(
            f"http://127.0.0.1:8000/health/{args.endpoint}", timeout=args.timeout
        ):
            pass
    except (URLError, TimeoutError) as error:
        parser.exit(1, f"Buddy {args.endpoint} probe failed: {error}\n")


if __name__ == "__main__":
    main()
