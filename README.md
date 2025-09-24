# osh - Odoo Scripts & Helpers

osh rassemble des utilitaires en ligne de commande concus pour industrialiser la gestion
des depots Odoo chez Apik. Le paquet fournit des scripts coherents pour piloter les
sous-modules Git, generer la documentation des addons et normaliser les manifestes,
afin de garder des projets multi-depots sous controle.

## Pourquoi utiliser osh ?

- Automatise l ajout, la verification et le nettoyage des sous-modules Git.
- Centralise la generation de listes et de tableaux d addons directement depuis les manifestes.
- Normalise les manifestes Odoo (en-tetes, mainteneurs, options) tout en preservant les commentaires.
- Fournit des scripts reproductibles pour les pipelines CI et les scripts de bootstrap projet.

## Installation

Prerequis : Python 3.8+, Git et un shell POSIX (bash) disponible sur la machine.

### Depuis GitHub (recommande)

```bash
pip install git+https://github.com/apikcloud/osh.git
```

### Developpement local

```bash
git clone https://github.com/apikcloud/osh.git
cd osh
pip install -e .
```

## Prise en main rapide

```bash
# Ajouter un sous-module OCA et creer des liens symboliques pour chaque addon
osh-sub-add https://github.com/OCA/server-ux.git -b 18.0 --auto-symlinks

# Inventorier tous les addons disponibles dans les sous-modules
osh-addons-list --format json > addons.json

# Reformatter tous les manifestes __manifest__.py d un dossier addons
osh-man-rewrite --addons-dir ./addons --check
```

## Commandes principales

### Gestion des sous-modules

- `osh-sub-add URL -b BRANCHE [options]` : ajoute un sous-module dans `.third-party/<ORG>/<REPO>` et
  peut creer des symlinks vers les addons du depot. Options clefs :
  - `--auto-symlinks` pour symlinker automatiquement chaque addon detecte.
  - `--addons` pour specifier une liste d addons a lier.
  - `--dry-run` pour visualiser le plan sans executer.
  - `--no-commit` pour laisser les modifications en staging.
- `osh-sub-check` : verifie que tous les sous-modules residuent sous `.third-party/` et qu au moins un
  lien symbolique pointe vers chacun d eux.
- `osh-sub-rewrite [options]` : reecrit les chemins des sous-modules selon leur URL, deplace les dossiers,
  met a jour `.gitmodules` et corrige les symlinks. Ajoutez `--dry-run` pour inspecter les changements,
  `--yes` pour tout accepter et `--no-commit` pour revoir le commit propose.
- `osh-sub-prune` : detecte les sous-modules sans symlinks associes et propose de les supprimer proprement
  (deinit Git, suppression des traces sous `.git/modules`).
- `osh-sub-clean [--reset]` : supprime les dossiers `third-party` ou `.third-party` vides puis relance
  `git submodule update --init --recursive`. L option `--reset` effectue un `git reset --hard`
  avant le nettoyage.
- `osh-sub-flatten [PATH]` : remplace les symlinks trouves a la racine de `PATH` par le contenu reel du
  depot cible (copie recursive). Pratique pour figer un livrable sans liens symboliques.

### Inventaire des addons

- `osh-addons-list [--format text|json|csv] [--only nom] [--init-missing]` : liste tous les addons
  detectes dans les sous-modules, avec le chemin relatif, l URL et la branche configures. Le format
  `json` ou `csv` facilite l exploitation automatique.
- `osh-addons-table [options]` : remplace les marqueurs `[//]: # (addons)` dans un README par une table
  Markdown construite depuis les manifestes. Options :
  - `--addons-dir` pour definir l emplacement des addons (defaut `.`).
  - `--readme-path` pour cibler un autre fichier markdown.
  - `--commit/--no-commit` pour controler l envoi d un commit automatique.

### Normalisation des manifestes Odoo

- `osh-man-rewrite` : applique un transformateur LibCST qui corrige les fautes de clefs (`mainteners` ->
  `maintainers`), remplace les noms par les comptes GitHub, ordonne les dependances, assure la presence
  des en-tetes standards et peut fonctionner en `--dry` (lecture seule) ou `--check` (code de retour 1 si
  un fichier devrait changer).
- `osh-man-fix` : outil historique base sur Black pour reformater un manifeste individuel. Il reste utile
  pour experimenter mais `osh-man-rewrite` est recommande dans les workflows modernes.

## Integrations et bonnes pratiques

- Ajoutez `osh-man-rewrite --check` dans vos pipelines CI pour garantir des manifestes homogenes.
- Combinez `osh-addons-list` avec `jq` ou `csvkit` pour controler l inventaire des modules.
- Utilisez `osh-sub-rewrite --dry-run` avant de partager un plan de migration de sous-modules.

## Support et contributions

Les scripts sont fournis tels quels par l equipe Apik. Les contributions sont les bienvenues via
pull request sur le depot GitHub. Pour developper :

```bash
pip install -e .[dev]  # optionnel : ajoutez vos dependances de dev
```

Puis lancez les commandes directement depuis votre environnement virtuel. Publiez vos correctifs avec
un resume clair et ajoutez des tests ou des fragments de changelog lorsque c est pertinent.

## Licence

Ce projet est publie sous licence AGPL-3.0-only. Consultez le fichier `LICENSE` ou
<https://www.gnu.org/licenses/agpl-3.0.html> pour plus de details.
