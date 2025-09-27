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
)
from osh.utils import date_from_string


@dataclass
class ImageInfo:
    registry: str
    repository: str
    major_version: float
    release: Optional[date]
    enterprise: bool
    legacy: bool


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
        y, mth, d = int(release_str[0:4]), int(release_str[4:6]), int(release_str[6:8])
        release = date(y, mth, d)

    return ImageInfo(
        registry=registry,
        repository=repository,
        major_version=major_version,
        release=release,
        enterprise=enterprise,
        legacy=legacy,
    )


def fetch_odoo_images(collections: Optional[list] = None) -> list:
    if collections is None:
        collections = DOCKER_COLLECTIONS
    data = make_get(ODOO_IMAGES_URL)

    return data


def check_image(image: ImageInfo):
    if image.registry not in DOCKER_RECOMMENDED_REGISTRIES:
        if image.registry in DOCKER_DEPRECATED_REGISTRIES:
            warn_deprecated_registry(image.registry)
        if image.registry in DOCKER_WARN_REGISTRIES:
            warn_unusual_registry(image.registry)


def find_available_images(release: date, enterprise: bool, version: float):
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

    available = fetch_odoo_images()
    edition = "enterprise" if enterprise else "community"

    def filter_out(item):
        if (
            item["version"] == version
            and item["edition"] == edition
            and date_from_string(item["release"]) >= release
            and item["collection"] in DOCKER_COLLECTIONS
        ):
            return item

    items = list(filter(filter_out, available))

    if not items:
        return []

    items = sorted(items, key=lambda item: item["release"], reverse=True)

    def improve(item):
        delta = abs((release - date_from_string(item["release"])).days)

        return {
            "registry": item["org"],
            "delta": delta,
            "image": item["image"],
        }

    return list(map(improve, items))
