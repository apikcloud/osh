import re
from dataclasses import dataclass
from datetime import date

from osh.compat import Optional
from osh.exceptions import (
    warn_deprecated_registry,
    warn_unusual_registry,
)
from osh.net import make_get
from osh.settings import (
    DOCKER_COLLECTIONS,
    DOCKER_DEPRECATED_REGISTRIES,
    DOCKER_RECOMMENDED_REGISTRIES,
    DOCKER_WARN_REGISTRIES,
    ODOO_IMAGES_URL,
    RELEASE_WARN_AGE_DAYS,
)
from osh.utils import date_from_string, render_table


@dataclass
class ImageInfo:
    image: str
    registry: str
    repository: str
    major_version: float
    release: Optional[date]
    enterprise: bool
    legacy: bool = False
    delta: int = 0  # days since release, to be filled later
    collection: Optional[str] = None  # to be filled later

    @property
    def source(self) -> str:
        return f"{self.registry}/{self.repository}"

    @property
    def edition(self) -> str:
        return "enterprise" if self.enterprise else "community"

    @property
    def age(self) -> Optional[int]:
        if self.release:
            return (date.today() - self.release).days
        return None

    @classmethod
    def from_raw_dict(cls, vals: dict):
        return cls(
            **{
                "image": vals["image"],
                "registry": vals["org"],
                "repository": vals["repo"],
                "major_version": float(vals["version"]),
                "release": date_from_string(vals["release"]),
                "enterprise": vals["edition"] == "enterprise",
                "collection": vals.get("collection"),
            }
        )


def parse_image_tag(tag: str) -> ImageInfo:
    """
    Parse an Odoo Docker image tag into its components.

    Expected patterns:
      <registry>/<repository>:<major>[.0][-<YYYYMMDD>][-enterprise][-legacy]

    Examples:
      odoo:19
      apik/odoo:19.0-20250919-enterprise
    """
    # Defaults
    registry = "odoo"
    repository = "odoo"
    major_version: float
    release: Optional[date] = None
    enterprise = False
    legacy = False

    # Split registry/repository and tag
    if ":" not in tag:
        raise ValueError(f"Invalid image tag: {tag}")
    left, tag_part = tag.split(":", 1)

    # Handle registry/repository
    if "/" in left:
        registry, repository = left.split("/", 1)
    else:
        registry = left
        repository = "odoo"

    # Extract flags
    if "enterprise" in tag_part:
        enterprise = True
        tag_part = tag_part.replace("-enterprise", "")
    if "legacy" in tag_part:
        legacy = True
        tag_part = tag_part.replace("-legacy", "")

    # Match version and optional release date
    m = re.match(r"^(?P<version>\d+(?:\.\d+)?)(?:-(?P<release>\d{8}))?$", tag_part)
    if not m:
        raise ValueError(f"Unrecognized tag format: {tag_part}")

    version_str = m.group("version")
    release_str = m.group("release")

    major_version = float(version_str)

    if release_str:
        release = date_from_string(release_str)

    return ImageInfo(
        image=tag,
        registry=registry,
        repository=repository,
        major_version=major_version,
        release=release,
        enterprise=enterprise,
        legacy=legacy,
    )


def fetch_odoo_images(collections: Optional[list] = None) -> list:
    # {
    #     "id": 976836335,
    #     "last_updated": "2025-09-21T13:03:37.077452Z",
    #     "name": "19.0-20250921-enterprise",
    #     "org": "apik",
    #     "repo": "odoo",
    #     "image": "apik/odoo:19.0-20250921-enterprise",
    #     "full_size": 779130948,
    #     "digest": "sha256:ca68c876ab9d614e27df74ec4e954d9a466c576a6a6c7c24d6ae8cde0a610683",
    #     "state": null,
    #     "collection": "production",
    #     "version": 19,
    #     "edition": "enterprise",
    #     "release": "20250921"
    # },

    if collections is None:
        collections = DOCKER_COLLECTIONS
    data = make_get(ODOO_IMAGES_URL)

    items = [ImageInfo.from_raw_dict(vals) for vals in data]

    def filter_out(item):
        if item.collection in collections:
            return item

    return list(filter(filter_out, items))


def check_image(image: ImageInfo, strict: bool = True) -> list:
    warnings = []
    recommmended = ", ".join(DOCKER_RECOMMENDED_REGISTRIES)
    if image.registry not in DOCKER_RECOMMENDED_REGISTRIES:
        if image.registry in DOCKER_DEPRECATED_REGISTRIES:
            if strict:
                warn_deprecated_registry(image.registry)
            else:
                warnings.append(
                    f"You should use one of these registries ({recommmended})"
                    f" as a replacement for '{image.registry}'."
                )

        if image.registry in DOCKER_WARN_REGISTRIES:
            if strict:
                warn_unusual_registry(image.registry)
            else:
                warnings.append(
                    f"You should use one of these registries ({recommmended})"
                    f" as a replacement for '{image.registry}'."
                )

    if image.age and image.age > RELEASE_WARN_AGE_DAYS:
        warnings.append(
            f"The current Odoo image is {image.age} days old, consider updating it",
        )

    return warnings


def find_available_images(release: date, enterprise: bool, version: float) -> list:
    available = fetch_odoo_images()

    # TODO: improve filtering, add conditions on release date
    def filter_out(item):
        if (
            item.major_version == version
            and item.enterprise == enterprise
            and item.release > release
            and item.collection in DOCKER_COLLECTIONS
        ):
            return item

    items = list(filter(filter_out, available))

    if not items:
        return []

    items = sorted(items, key=lambda item: item.release, reverse=True)

    def improve(item):
        item.delta = abs((release - item.release).days)
        return item

    return list(map(improve, items))


def format_available_images(images: list, include_index: bool = False) -> str:
    if not images:
        return ""

    rows = []

    headers = ["Release", "Delta (days)", "Source"]
    if include_index:
        headers.insert(0, "Index")

    for item in images:
        rows.append([item.release.isoformat(), item.delta, item.source])

    return render_table(rows, headers=headers, index=include_index)
