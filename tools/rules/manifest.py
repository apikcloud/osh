import libcst as cst
import libcst.matchers as m
from fixit import LintRule


class OdooManifestAuthorMaintainers(LintRule):
    MESSAGE = "Invalid Odoo manifest metadata."
    ALLOWED_HANDLES = {"apikcloud", "aurelien-roy", "apik-dev"}  # extend as needed

    VALID = [
        """{
            "name": "APIK DATA",
            "author": "Apik",
            "maintainers": ["apikcloud", "aurelien-roy"]
        }""",
        """manifest = {
            "author": "Apik",
            "maintainers": ["apik-dev"]
        }""",
    ]

    INVALID = [
        """{"author": "SomeoneElse", "maintainers": ["random"]}""",
        """{"author": "Apik", "maintainers": []}""",
        """{"author": "Apik"}""",
        """{"maintainers": ["apikcloud"]}""",
    ]

    def _extract_top_level_dict(self, module: cst.Module):
        # Case 1: bare dict at top-level: { ... }
        if module.body and m.matches(
            module.body[0], m.SimpleStatementLine(body=[m.Expr(value=m.Dict())])
        ):
            return m.extract(module.body[0], m.SimpleStatementLine(body=[m.Expr(value=m.Dict())]))[
                0
            ].value

        # Case 2: assigned dict: manifest = { ... }  (any name)
        if module.body and m.matches(
            module.body[0],
            m.SimpleStatementLine(
                body=[m.Assign(targets=[m.AssignTarget(target=m.Name())], value=m.Dict())]
            ),
        ):
            return m.extract(
                module.body[0],
                m.SimpleStatementLine(
                    body=[m.Assign(targets=[m.AssignTarget(target=m.Name())], value=m.Dict())]
                ),
            )[0].value

        return None

    def visit_Module(self, node: cst.Module) -> None:
        manifest = self._extract_top_level_dict(node)
        if manifest is None:
            # Not an Odoo manifest file; stay quiet.
            return

        # Build key -> value map for string keys only
        kv = {}
        for el in manifest.elements or []:
            if el and el.key and m.matches(el.key, m.SimpleString()):
                key = el.key.evaluated_value
                kv[key] = el.value

        # ---- author ----
        author = kv.get("author")
        if author is None:
            self.report(manifest, message="Manifest is missing 'author' key.")
        elif not (
            m.matches(author, m.SimpleString())
            and getattr(author, "evaluated_value", None) == "Apik"
        ):
            self.report(author, message="Manifest 'author' must be exactly 'Apik'.")

        # ---- maintainers ----
        maintainers = kv.get("maintainers")
        if maintainers is None:
            self.report(manifest, message="Manifest is missing 'maintainers' key.")
            return

        if not m.matches(maintainers, m.List()):
            self.report(maintainers, message="'maintainers' must be a list of GitHub handles.")
            return

        # Extract plain string items
        items = []
        for it in getattr(maintainers, "elements", []) or []:
            val = getattr(it, "value", None)
            if not m.matches(val, m.SimpleString()):
                self.report(it, message="'maintainers' must contain only string handles.")
                return
            items.append(val.evaluated_value)

        if not items:
            self.report(maintainers, message="'maintainers' list must not be empty.")
            return

        unknown = [h for h in items if h not in self.ALLOWED_HANDLES]
        if unknown:
            self.report(
                maintainers,
                message=(
                    f"'maintainers' contains unknown handle(s): {', '.join(sorted(unknown))}. "
                    f"Allowed: {', '.join(sorted(self.ALLOWED_HANDLES))}."
                ),
            )
