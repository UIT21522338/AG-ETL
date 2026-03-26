#!/usr/bin/env python
"""Thin wrapper entrypoint for Agent 2 error diagnosis.

Usage:
  python agents/agent-2-error-diagnosis/run.py
  python agents/agent-2-error-diagnosis/run.py --dry-run
  python agents/agent-2-error-diagnosis/run.py --loop
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Forward all CLI args to src/agent_2_main.py."""
    entrypoint = Path(__file__).resolve().parent / "src" / "agent_2_main.py"
    cmd = [sys.executable, str(entrypoint), *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
