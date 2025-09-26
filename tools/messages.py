GIT_NEW_ADDONS = "chore: new addons"
GIT_IGNORED_ADDONS = "chore: ignored addons"
GIT_REWRITE_SUBMODULES = "chore: rewrite submodule paths based on remote URL"
GIT_PRUNE_SUBMODULES = "chore: remove unused submodules"
GIT_ADD_SUBMODULE = "chore: add submodule {name}"
GIT_ADD_SUBMODULE_DESC = """
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
