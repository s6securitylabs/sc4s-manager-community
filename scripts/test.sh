#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

resolve_default_test_path() {
  local kind="$1"
  PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python3 - "$kind" <<'PY'
from sc4s_manager.test_paths import default_coverage_file, default_pytest_cache_dir, default_test_venv_dir
import sys

kind = sys.argv[1]
if kind == "venv":
    print(default_test_venv_dir())
elif kind == "pytest_cache":
    print(default_pytest_cache_dir())
elif kind == "coverage_file":
    print(default_coverage_file())
else:  # pragma: no cover - defensive shell bridge
    raise SystemExit(f"unknown test path kind: {kind}")
PY
}

VENV_DIR="${SC4S_MANAGER_TEST_VENV:-$(resolve_default_test_path venv)}"
if [ ! -x "$VENV_DIR/bin/python" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
. "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install pytest pytest-cov jsonschema >/dev/null
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_packs.py
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_pack_fixtures.py
PYTEST_CACHE_DIR="${SC4S_MANAGER_PYTEST_CACHE:-$(resolve_default_test_path pytest_cache)}"
PYTEST_ARGS=("$@")
TARGETED_TEST_RUN=0
EXPLICIT_COVERAGE_ARGS=0
for arg in "$@"; do
  case "$arg" in
    --cov|--cov=*|--cov-report|--cov-report=*|--cov-fail-under|--cov-fail-under=*)
      EXPLICIT_COVERAGE_ARGS=1
      ;;
    -*)
      ;;
    *)
      TARGETED_TEST_RUN=1
      ;;
  esac
done
if [ "$TARGETED_TEST_RUN" -eq 1 ] && [ "$EXPLICIT_COVERAGE_ARGS" -eq 0 ]; then
  # pyproject enforces full-suite coverage. Disable coverage for targeted
  # pack/schema checks so service-owned-tree smoke commands can pass
  # without writing repo-local coverage or failing on unrelated modules.
  PYTEST_ARGS=(--no-cov "${PYTEST_ARGS[@]}")
fi
COVERAGE_FILE="${SC4S_MANAGER_COVERAGE_FILE:-$(resolve_default_test_path coverage_file)}" PYTHONDONTWRITEBYTECODE=1 python -m pytest -o cache_dir="$PYTEST_CACHE_DIR" "${PYTEST_ARGS[@]}"
