#!/usr/bin/env python3

import logging
import os
from pathlib import Path

from osh.exceptions import MissingMandatoryFiles, MissingRecommendedFiles
from osh.settings import (
    PROJECT_FILE_ODOO_VERSION,
    PROJECT_FILE_PACKAGES,
    PROJECT_FILE_REQUIREMENTS,
    PROJECT_MANDATORY_FILES,
    PROJECT_RECOMMENDED_FILES,
)
from osh.utils import read_and_parse

NEW_LINE = "\n"


def check_project(path: Path, strict: bool = True):
    files = set(os.listdir(path))
    missing_files = PROJECT_MANDATORY_FILES.difference(files)
    if missing_files:
        raise MissingMandatoryFiles(missing_files)

    missing_recommended_files = PROJECT_RECOMMENDED_FILES.difference(files)
    if missing_recommended_files:
        if strict:
            raise MissingRecommendedFiles(missing_recommended_files)
        else:
            logging.warning(MissingRecommendedFiles.message.format(files=missing_recommended_files))


def parse_packages(path: Path) -> list:
    return read_and_parse(path / PROJECT_FILE_PACKAGES)


def parse_requirements(path) -> list:
    return read_and_parse(path / PROJECT_FILE_REQUIREMENTS)


def parse_odoo_version(path) -> str:
    res = read_and_parse(path / PROJECT_FILE_ODOO_VERSION)
    if not res:
        raise ValueError()
    return res[0]
