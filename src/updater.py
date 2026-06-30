import argparse
import subprocess
import sys
import time
from pathlib import Path

from packaging.version import InvalidVersion, Version
from tqdm import tqdm

from common import logger, DEV_ENV
from common.admin import ensure_admin_privileges
from version_installer.installer import VersionInstaller

ensure_admin_privileges()

parser = argparse.ArgumentParser()
parser.add_argument(
    '-v',
    '--version',
    type=str,
    help='Version to install. Defaults to the latest version.',
)
parser.add_argument(
    '-b',
    '--beta',
    action='store_true',
    help='When looking for the latest version, also include beta versions.',
)
args = parser.parse_args()

version: Version | None = None
if args.version:
    try:
        version = Version(args.version)
    except InvalidVersion:
        logger.error(
            'Invalid version [%s], falling back to latest version.',
            args.version,
        )

install_dir = Path('test-install')

with tqdm(total=100) as progress_bar:
    VersionInstaller.install_version(
        install_dir=install_dir,
        set_progress=lambda p: progress_bar.update(p - progress_bar.n),
        set_status=progress_bar.write,
        version=version,
        check_beta=args.beta,
    )
