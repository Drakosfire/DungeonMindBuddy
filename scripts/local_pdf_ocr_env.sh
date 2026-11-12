#!/usr/bin/env bash

# Resolve the existing local DeepSeek OCR 2 checkout and cache for the Buddy
# launcher. Every path remains overridable by the local operator.
configure_local_pdf_ocr() {
  local buddy_root="${1:?Buddy checkout root is required}"
  local workspace_root="${DUNGEONMIND_WORKSPACE_ROOT:-$(cd "${buddy_root}/.." && pwd)}"
  local projects_root="${DUNGEONMIND_PROJECTS_ROOT:-$(cd "${workspace_root}/.." && pwd)}"
  local hub_cache="${HF_HUB_CACHE:-${HF_HOME:-${projects_root}/.cache/huggingface}/hub}"
  local model_cache="${hub_cache}/models--deepseek-ai--DeepSeek-OCR-2"
  local model_revision=""
  local default_checkpoint=""

  if [[ -f "${model_cache}/refs/main" ]]; then
    # Hugging Face ref files may omit the final newline. Preserve the value
    # read at EOF without letting strict-mode callers abort configuration.
    IFS= read -r model_revision < "${model_cache}/refs/main" || true
  fi
  if [[ "${model_revision}" =~ ^[a-f0-9]{40}$ ]]; then
    default_checkpoint="${model_cache}/snapshots/${model_revision}"
  fi

  local ocr_python="${BUDDY_OCR_PYTHON:-${workspace_root}/RulesIngestion/.venv-deepseek-ocr2/bin/python}"
  local ocr_command="${BUDDY_OCR_COMMAND:-${workspace_root}/GenerationEngine/GenerationEngine/scripts/run_local_ocr.py}"
  local ocr_checkpoint="${BUDDY_OCR_CHECKPOINT:-${default_checkpoint}}"

  if [[ -x "${ocr_python}" && -f "${ocr_command}" && -d "${ocr_checkpoint}" ]]; then
    export BUDDY_OCR_PYTHON="${ocr_python}"
    export BUDDY_OCR_COMMAND="${ocr_command}"
    export BUDDY_OCR_CHECKPOINT="${ocr_checkpoint}"
    printf '[run] Local PDF OCR configured with the cached DeepSeek OCR 2 model.\\n' >&2
    return 0
  fi

  unset BUDDY_OCR_PYTHON BUDDY_OCR_COMMAND BUDDY_OCR_CHECKPOINT
  printf '[run] Local PDF OCR unavailable: set BUDDY_OCR_PYTHON, BUDDY_OCR_COMMAND, and BUDDY_OCR_CHECKPOINT to local assets.\\n' >&2
}
