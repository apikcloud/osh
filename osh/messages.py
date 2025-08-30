GIT_ADDONS_NEW = "chore: new addons"
GIT_ADDONS_IGNORED = "chore: ignored addons"
GIT_SUBMODULES_REWRITE = "chore: rewrite submodule paths based on remote URL"
GIT_SUBMODULES_PRUNE = "chore: remove unused submodules"
GIT_SUBMODULE_ADD = "chore: add submodule {name}"
GIT_SUBMODULE_ADD_DESC = """
- url: {url}
- branch: {branch}
- path: {path}
- created symlinks: {symlinks}
"""
ADD_SUBMODULES_PLAN = """
=== Plan ===
"Repo Root         : {repo}
"URL               : {url}
"Branch            : {branch}
"Submodule name    : {name}
"Target path       : {path}
"Auto symlinks     : {auto_symlinks}
"Addons            : {addons}
"Commit at the end : {commit_or_not}
"Dry-run           : {dry_run}
==============
"""
GIT_ODOO_IMAGE_UPDATE = "chore: update odoo image to '{new}'\n\nFrom '{old}', {days} day(s) newer."
GIT_SUBMODULES_RENAME = "chore: rename submodules to new naming scheme"
GIT_MATERIALIZE_ADDONS = "chore: materialize addon(s) {names}"
GIT_UPDATE_PRE_COMMIT_EXCLUDE = "chore: update pre-commit exclusions"
