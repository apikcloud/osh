#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./rewrite-symlinks.sh           # dry-run (montre ce qui changerait)
#   ./rewrite-symlinks.sh --write   # applique les changements
#
# Fait :
#  - Trouve tous les symlinks du repo (hors .git)
#  - Si leur cible contient 'third-party', remplace par '.third-party'
#  - Préserve les chemins relatifs/absolus (substitution simple)
#  - Utilise ln -sfn pour réécrire le lien sans suivre la cible
#
# Conseil d'ordre: d'abord 'mv third-party .third-party', puis ce script en --write

WRITE=0
if [[ "${1:-}" == "--write" ]]; then
  WRITE=1
fi

# Aller à la racine du repo si possible
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  cd "$(git rev-parse --show-toplevel)"
fi

changed=0
scanned=0

# Trouver tous les symlinks (hors .git), null-delimited pour gérer espaces
while IFS= read -r -d '' link; do
  ((scanned++)) || true

  # Lire la cible du lien (relative ou absolue)
  target="$(readlink "$link")" || continue

  # On ne touche qu'aux cibles contenant 'third-party'
  if [[ "$target" == *third-party* ]]; then
    # Remplacer toutes les occurrences (au cas où)
    new_target="${target//third-party/.third-party}"

    if [[ "$new_target" == "$target" ]]; then
      continue
    fi

    echo "↪ $link"
    echo "   $target"
    echo "   → $new_target"

    if (( WRITE == 1 )); then
      # Réécrit le lien sans suivre la cible (-n) et en forçant (-f)
      ln -sfn -- "$new_target" "$link"
      ((changed++)) || true
    fi
  fi
done < <(find . -path ./.git -prune -o -type l -print0)

if (( WRITE == 1 )); then
  echo
  echo "✅ Terminé : $changed lien(s) mis à jour sur $scanned scanné(s)."
else
  echo
  echo "🔎 Dry-run : relance avec --write pour appliquer les changements."
  echo "   (symlinks scannés : $scanned)"
fi
