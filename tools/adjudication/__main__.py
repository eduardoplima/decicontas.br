"""``python -m tools.adjudication [--port 8765]`` — serve the adjudication tool locally."""

from __future__ import annotations

import argparse

import uvicorn

from tools.adjudication.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
