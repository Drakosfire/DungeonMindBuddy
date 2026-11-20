#!/usr/bin/env bash

# Resolve the existing local DeepSeek OCR 2 checkout and cache for the Buddy
# launcher. Every path remains overridable by the local operator.
configure_local_pdf_ocr() {
  local buddy_root="${1:?Buddy checkout root is required}"
  local ocr_python="${BUDDY_OCR_PYTHON:-}"
  local ocr_command="${BUDDY_OCR_COMMAND:-}"
  local ocr_checkpoint="${BUDDY_OCR_CHECKPOINT:-}"

  if [[ -z "${ocr_python}" || -z "${ocr_command}" || -z "${ocr_checkpoint}" ]]; then
    local workspace_root="${DUNGEONMIND_WORKSPACE_ROOT:-}"
    local projects_root="${DUNGEONMIND_PROJECTS_ROOT:-}"
    local projects_root_from_checkout=""

    if [[ -z "${workspace_root}" ]]; then
      local search_root
      search_root="$(cd "${buddy_root}" && pwd -P)"
      while :; do
        if [[ -d "${search_root}/RulesIngestion" \
          && -f "${search_root}/GenerationEngine/GenerationEngine/scripts/run_local_ocr.py" ]]; then
          workspace_root="${search_root}"
          if [[ "${search_root%/*}" == */Projects ]]; then
            projects_root_from_checkout="${search_root%/*}"
          fi
          break
        fi

        # Codex checkouts live under Projects/.codex/<lane>/DungeonMindBuddy,
        # while the shared OCR assets live beside them in Projects/DungeonOverMind.
        if [[ "${search_root##*/}" == "Projects" \
          && -d "${search_root}/DungeonOverMind/RulesIngestion" \
          && -f "${search_root}/DungeonOverMind/GenerationEngine/GenerationEngine/scripts/run_local_ocr.py" ]]; then
          workspace_root="${search_root}/DungeonOverMind"
          projects_root_from_checkout="${search_root}"
          break
        fi

        if [[ "${search_root}" == "/" ]]; then
          break
        fi
        search_root="$(dirname "${search_root}")"
      done
    fi

    workspace_root="${workspace_root:-$(cd "${buddy_root}/.." && pwd)}"
    projects_root="${projects_root:-${projects_root_from_checkout:-$(cd "${workspace_root}/.." 2>/dev/null && pwd || dirname -- "${workspace_root}")}}"
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

    ocr_python="${BUDDY_OCR_PYTHON:-${workspace_root}/RulesIngestion/.venv-deepseek-ocr2/bin/python}"
    ocr_command="${BUDDY_OCR_COMMAND:-${workspace_root}/GenerationEngine/GenerationEngine/scripts/run_local_ocr.py}"
    ocr_checkpoint="${BUDDY_OCR_CHECKPOINT:-${default_checkpoint}}"

  fi

  if [[ -x "${ocr_python}" && -f "${ocr_command}" && -d "${ocr_checkpoint}" ]]; then
    export BUDDY_OCR_PYTHON="${ocr_python}"
    export BUDDY_OCR_COMMAND="${ocr_command}"
    export BUDDY_OCR_CHECKPOINT="${ocr_checkpoint}"
    printf '[run] Local PDF OCR configured with the cached DeepSeek OCR 2 model.\n' >&2
    return 0
  fi

  unset BUDDY_OCR_PYTHON BUDDY_OCR_COMMAND BUDDY_OCR_CHECKPOINT
  printf '[run] Local PDF OCR unavailable: set BUDDY_OCR_PYTHON, BUDDY_OCR_COMMAND, and BUDDY_OCR_CHECKPOINT to local assets.\n' >&2
}
