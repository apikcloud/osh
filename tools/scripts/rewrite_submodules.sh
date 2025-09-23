#!/usr/bin/env bash
set -euo pipefail

# Rewrite submodule paths and fix symlinks.
# Usage:
#   ./rewrite-submodule-paths.sh [ROOT] [FROM [TO]] [--dry-run]
# Defaults:
#   ROOT = repo toplevel
#   FROM = "third-party"
#   TO   = ".third-party"

# --- parse args (ROOT if $1 is a dir) ---
ROOT=""
FROM="third-party"
TO=".third-party"
DRY_RUN=""

arg1="${1:-}"
arg2="${2:-}"
arg3="${3:-}"
arg4="${4:-}"

is_dir_arg1=0
if [[ -n "${arg1}" && -d "${arg1}" ]]; then
  ROOT="$(cd "${arg1}" && pwd -P)"
  is_dir_arg1=1
fi

# Shift-like behavior
if [[ ${is_dir_arg1} -eq 1 ]]; then
  FROM="${arg2:-${FROM}}"
  TO="${arg3:-${TO}}"
  [[ "${arg4:-}" == "--dry-run" || "${arg3:-}" == "--dry-run" ]] && DRY_RUN=1 || true
else
  FROM="${arg1:-${FROM}}"
  TO="${arg2:-${TO}}"
  [[ "${arg3:-}" == "--dry-run" || "${arg2:-}" == "--dry-run" ]] && DRY_RUN=1 || true
fi

# Discover repo root if not provided
if [[ -z "${ROOT}" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -z "${ROOT}" ]] && { echo "Error: not inside a Git repo and no ROOT provided."; exit 1; }
fi
cd "${ROOT}"

echo "Repo: ${ROOT}"
echo "Rewrite segment: '${FROM}' -> '${TO}'${DRY_RUN:+ (dry-run)}"
echo

if [[ ! -f .gitmodules ]]; then
  echo "No .gitmodules found. Skipping submodule path updates."
else
  mapfile -t LINES < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' || true)

  if [[ ${#LINES[@]} -eq 0 ]]; then
    echo "No submodule 'path' entries found in .gitmodules."
  else
    KEYS=(); OLD_PATHS=(); NEW_PATHS=()
    for LINE in "${LINES[@]}"; do
      KEY="${LINE%% *}"
      VAL="${LINE#* }"
      if [[ "${VAL}" == *"${FROM}"* ]]; then
        NEW="${VAL//${FROM}/${TO}}"
        echo "[plan] path: ${VAL} -> ${NEW}"
        KEYS+=("${KEY}")
        OLD_PATHS+=("${VAL}")
        NEW_PATHS+=("${NEW}")
      fi
    done

    if [[ ${#OLD_PATHS[@]} -eq 0 ]]; then
      echo "Nothing in .gitmodules contains '${FROM}'."
    elif [[ -z "${DRY_RUN}" ]]; then
      for i in "${!KEYS[@]}"; do
        git config -f .gitmodules "${KEYS[$i]}" "${NEW_PATHS[$i]}"
      done
      git add .gitmodules
    fi
  fi
fi

# Physically move submodule folders when their path changed
if [[ -z "${DRY_RUN}" && ${#OLD_PATHS[@]:-0} -gt 0 ]]; then
  for i in "${!OLD_PATHS[@]}"; do
    SRC="${OLD_PATHS[$i]}"
    DST="${NEW_PATHS[$i]}"

    # Ensure SRC exists (init if needed)
    if [[ ! -e "${SRC}" ]]; then
      echo "[info] '${SRC}' missing; trying submodule init"
      git submodule update --init -- "${SRC}" || true
    fi

    if [[ -e "${SRC}" && "${SRC}" != "${DST}" ]]; then
      mkdir -p "$(dirname -- "${DST}")"
      echo "[mv] ${SRC} -> ${DST}"
      git mv -k -- "${SRC}" "${DST}" || {
        # If git mv fails (e.g., due to symlink), fallback:
        echo "[fallback] git mv failed; doing manual move"
        mv -- "${SRC}" "${DST}"
        git add -A -- "${DST}"
        git rm -f --cached "${SRC}" || true
      }
    fi
  done

  # Sync and update submodule metadata
  git submodule sync --recursive
  git submodule update --init --recursive
fi

# Rewrite symlink targets anywhere in the repo that contain FROM
echo
echo "[scan] fixing symlink targets containing '${FROM}' ..."
while IFS= read -r -d '' link; do
  tgt="$(readlink -- "$link" || true)"
  [[ -z "$tgt" ]] && continue
  if [[ "$tgt" == *"${FROM}"* ]]; then
    new_tgt="${tgt//${FROM}/${TO}}"
    echo "[plan] $link : $tgt -> $new_tgt"
    if [[ -z "${DRY_RUN}" ]]; then
      ln -snf -- "$new_tgt" "$link"
    fi
  fi
done < <(find . -type l -print0)

echo
echo "Done.${DRY_RUN:+ (dry-run only)} Review changes with:"
echo "  git status && git diff --cached"
echo "Then commit:"
echo "  git commit -m \"chore: rewrite submodule paths: '${FROM}' -> '${TO}'\""
