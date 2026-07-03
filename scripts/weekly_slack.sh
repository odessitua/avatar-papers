#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
UPDATE_LOG="${LOG_DIR}/update.log"
SLACK_LOG="${LOG_DIR}/slack_weekly.log"

if [[ -f "${PROJECT_DIR}/.venv/bin/activate" ]]; then
    source "${PROJECT_DIR}/.venv/bin/activate"
else
    : "${CONDA_SH:=/home/ubuntu/miniconda3/etc/profile.d/conda.sh}"
    : "${CONDA_ENV:=f2v-3-5}"
    # shellcheck source=/dev/null
    source "${CONDA_SH}"
    conda activate "${CONDA_ENV}"
fi

cd "${PROJECT_DIR}"
set -a
source .env
set +a

echo "=== weekly_slack: pre-slack update at $(date -u +%FT%TZ) ===" >> "${UPDATE_LOG}"
python main.py update >> "${UPDATE_LOG}" 2>&1

echo "=== weekly_slack: sending slack report at $(date -u +%FT%TZ) ===" >> "${SLACK_LOG}"
python main.py slack-weekly --week last >> "${SLACK_LOG}" 2>&1
