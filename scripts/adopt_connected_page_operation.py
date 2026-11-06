"""Explicit one-file adoption; does not create pages or publish Graph changes."""
import argparse
from pathlib import Path

from apps.live_control_server.services.connected_page_authoring import adopt_connected_page_operation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("operation", type=Path)
    args = parser.parse_args()
    result = adopt_connected_page_operation(args.root, args.operation)
    print(f"Adopted {result['operation_id']} ({result['phase']})")


if __name__ == "__main__":
    main()
