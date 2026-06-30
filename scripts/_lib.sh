#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python_bin() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s\n' "${PYTHON}"
  elif [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    printf '%s\n' "${ROOT_DIR}/.venv/bin/python"
  elif command -v python >/dev/null 2>&1; then
    printf '%s\n' "python"
  else
    printf '%s\n' "python3"
  fi
}

tool_bin() {
  local tool="$1"

  if [[ -x "${ROOT_DIR}/.venv/bin/${tool}" ]]; then
    printf '%s\n' "${ROOT_DIR}/.venv/bin/${tool}"
  elif command -v "${tool}" >/dev/null 2>&1; then
    printf '%s\n' "${tool}"
  else
    printf 'Required tool not found: %s\n' "${tool}" >&2
    printf 'Install test dependencies with: %s -m pip install -r requirements_test.txt\n' "$(python_bin)" >&2
    return 127
  fi
}

