from dataclasses import dataclass
from datetime import date, datetime, timezone

from osh.compat import Optional
from osh.utils import date_from_string, format_datetime


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


@dataclass
class CommitInfo:
    author: str
    date: datetime
    email: str
    message: str
    sha: str

    @property
    def age(self) -> int:
        """
        Returns the integer number of days since the commit date (truncates partial days).
        """
        return (datetime.today().date() - self.date.date()).days

    @classmethod
    def from_string(cls, output: str, sep: str = ";") -> "CommitInfo":
        """ "--pretty=format:%h;%an;%ae;%ad;%s"
        1. sha
        2. author name
        3. author email
        4. date (ISO 8601 format)
        5. commit message
        """
        sha, author, email, date_str, message = output.split(sep, 4)
        commit_date = datetime.fromisoformat(date_str)
        return cls(
            sha=sha,
            author=author,
            email=email,
            date=commit_date,
            message=message,
        )

    def __str__(self) -> str:
        return f"{self.message} by {self.author} on {format_datetime(self.date)} ({self.sha})"


@dataclass
class WorfklowRunInfo:
    actor: str
    branch: str
    conclusion: str
    date: datetime
    event: str
    name: str
    sha: str
    status: str
    url: str

    @property
    def age(self) -> int:
        """
        Returns the integer number of days since the commit date (truncates partial days).
        """
        return (datetime.today().date() - self.date.date()).days

    @classmethod
    def from_dict(cls, vals: dict) -> "WorfklowRunInfo":
        # ISO8601 -> datetime (handles trailing 'Z')
        created = datetime.fromisoformat(vals["created_at"].replace("Z", "+00:00")).astimezone(
            timezone.utc
        )

        return cls(
            **{
                "name": vals["name"],
                "event": vals["event"],
                "status": vals["status"],
                "conclusion": vals["conclusion"],
                "sha": vals["head_sha"],
                "branch": vals["head_branch"],
                "date": created,
                "url": vals["url"],
                "actor": vals["actor"]["login"],
            }
        )

    def __str__(self) -> str:
        return f"{self.name} triggered by {self.event} on {self.branch} by {self.actor} ({self.status}/{self.conclusion})"  # noqa: E501
