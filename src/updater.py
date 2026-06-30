import argparse
import subprocess
import sys
import time
from pathlib import Path

from packaging.version import InvalidVersion, Version
from tqdm import tqdm

from common import logger, DEV_ENV, UPDATER_DIR
from common.admin import ensure_admin_privileges
from gui.gui_updater import UpdaterApp
from version_installer.installer import VersionInstaller


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
parser.add_argument(
    '-c',
    '--cli',
    action='store_true',
    help='Run in a terminal instead of the Toga app.',
)
parser.add_argument(
    '-s',
    '--skip-admin',
    action='store_true',
    help='Run without requiring admin privileges.',
)
args = parser.parse_args()

if not args.skip_admin:
    ensure_admin_privileges()

version: Version | None = None
if args.version:
    try:
        version = Version(args.version)
    except InvalidVersion:
        logger.error(
            'Invalid version [%s], falling back to latest version.',
            args.version,
        )

if args.cli:
    with tqdm(total=100) as progress_bar:
        VersionInstaller.install_version(
            install_dir=UPDATER_DIR,
            set_progress=lambda p: progress_bar.update(p - progress_bar.n),
            set_status=progress_bar.write,
            version=version,
            check_beta=args.beta,
        )
else:
    app = UpdaterApp(version, args.beta)
    app.main_loop()
