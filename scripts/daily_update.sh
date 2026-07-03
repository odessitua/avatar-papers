#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"

mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/update.log"

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

python main.py update >> "${LOG_FILE}" 2>&1
