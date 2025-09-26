# osh/compat.py
from __future__ import annotations

import sys
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Optional, Tuple

PY37 = sys.version_info < (3, 8)
PY38 = sys.version_info < (3, 9)
PY39 = sys.version_info < (3, 10)
PY311 = sys.version_info >= (3, 11)

# typing
try:
    from typing import Final, Literal, ParamSpec, Protocol, Self, TypedDict
except ImportError:  # 3.7–3.10
    from typing_extensions import (  # type: ignore
        Final,
        Literal,
        ParamSpec,
        Protocol,
        Self,
        TypedDict,
    )


# stdlib backports
try:
    import importlib.metadata as importlib_metadata  # py39+
except Exception:
    import importlib_metadata  # type: ignore

try:
    import tomllib  # py311+
except Exception:  # pragma: no cover
    import tomli as tomllib  # type: ignore

try:
    from zoneinfo import ZoneInfo  # py39+
except Exception:
    from backports.zoneinfo import ZoneInfo  # type: ignore

__all__ = [
    Protocol,
    TypedDict,
    Literal,
    Final,
    ParamSpec,
    Self,
    importlib_metadata,
    tomllib,
    ZoneInfo,
    Iterable,
    Mapping,
    Optional,
    Tuple,
    TYPE_CHECKING,
]
