import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
import subprocess
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable

from packaging.version import Version
from requests import Response, get
from requests.exceptions import RequestException  # pylint: disable=redefined-builtin

from common import logger
from common.exception import SCInstallerException
from common.i18n import _



class VersionInstaller:
    @classmethod
    def install_version(
        cls,
        install_dir: Path,
        set_status: Callable[[str], None],
        set_progress: Callable[[float], None],
        version: Version | None = None,
        check_beta: bool = False,
        avoid_path: Path | None = None,
        add_windows_firewall_rule: bool = False,
    ) -> str | None:
        """Install a version at the provided install directory.
        If no version is provided, search for the latest one.
        raises a SCInstallerException if it fails.
        params:
            - set_status: Function setting the status to display to users.
            - set_progress: Function setting the value of a progress bar.
                Takes as input values between 0 and 100.
            - version: The version to install. If not provided, search for the latest version.
            - check_beta: if True, latest version also includes beta versions
            - avoid_path: Prevent overwriting the files containing this path when installing.
        """
        set_progress(0)
        if not version:
            set_status(_('Searching for the latest version...'))
            version = cls._search_for_latest_version(check_beta)
            set_progress(10)
        download_url = cls._get_asset_url(version)
        set_status(
            _('Downloading version [{version}] from GitHub...').format(
                version=version
            )
        )
        response: Response = get(
            download_url, allow_redirects=True, timeout=10
        )
        set_progress(20)
        if response.status_code != 200:
            raise SCInstallerException(
                _('Downloading failed with code [{code}].').format(
                    code=response.status_code
                )
            )
        with tempfile.TemporaryDirectory() as _tmp_dir:
            tmp_dir = Path(_tmp_dir)
            downloaded_file = tmp_dir / cls._get_asset_name(version)
            set_progress(20)
            set_status(
                _(
                    'Writing downloaded archive to [{path}]...'
                ).format(path=downloaded_file)
            )
            downloaded_file.write_bytes(response.content)
            set_progress(30)

            install_dir.mkdir(exist_ok=True, parents=True)
            if sys.platform == 'win32':
                # For Windows: Unzip the file to a tmp location
                extract_dir = tmp_dir / f'sharly-chess-{version}'
                set_status(
                    _('Extracting archive to [{path}]...').format(path=extract_dir)
                )
                with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                control_file = extract_dir / 'tmp' / 'control_file.json'
                if control_file.exists():
                    set_progress(50)
                    set_status(_('Searching for missing files...'))
                    with open(control_file, 'r', encoding='utf8') as infile:
                        control_data: dict[str, Any] = json.loads(infile.read())
                    file_paths: list[str] = control_data['file_paths']
                    if any(
                        not (extract_dir / file_path).is_file()
                        for file_path in file_paths
                    ):
                        raise SCInstallerException(
                            _('Some files are missing from the downloading.')
                        )
                    control_file.unlink(missing_ok=True)
                set_progress(60)
                set_status(_('Unblocking files...'))
                for root_, __, files in os.walk(extract_dir):
                    for name in files:
                        path = os.path.join(root_, name)
                        # Remove Zone.Identifier ADS if it exists
                        ads_path = path + ':Zone.Identifier'
                        try:
                            os.remove(ads_path)
                            print(f'Unblocked: {path}')
                        except FileNotFoundError:
                            pass  # not blocked or already unblocked
                        except Exception as e:
                            print(f'Failed to unblock {path}: {e}')
                set_progress(70)
                cls._copy_dir_files(
                    src_dir=extract_dir,
                    dst_dir=install_dir,
                    set_progress=set_progress,
                    set_status=set_status,
                    progress_start=70,
                    progress_end=95,
                    avoid_path=avoid_path,
                )
                if add_windows_firewall_rule:
                    set_status(_('Adding windows firewall rule...'))
                    exe_path = install_dir / 'sharly-chess-3.exe'
                    command = (
                        'netsh advfirewall firewall add rule name="Sharly Chess" dir=in '
                        f'action=allow program="{exe_path.absolute()}" enable=yes profile=any'
                    )
                    try:
                        subprocess.run(command, shell=True, check=True)
                    except subprocess.CalledProcessError as ex:
                        logger.exception(ex)
                        raise SCInstallerException(_('Error while adding firewall rule.'))
            else:
                # For Mac: Handle the DMG file
                mount_point = tmp_dir / f'mount-{version}'
                try:
                    set_status(
                        _('Mounting DMG file to [{path}]...').format(path=mount_point)
                    )
                    # Mount the DMG
                    subprocess.run(
                        [
                            'hdiutil',
                            'attach',
                            str(downloaded_file),
                            '-mountpoint',
                            str(mount_point),
                        ],
                        check=True,
                    )
                    set_progress(60)
                    dmg_content = list(mount_point.iterdir())

                    if len(dmg_content) != 1 or dmg_content[0].is_dir():
                        raise SCInstallerException(
                            _('DMG does not contain exactly one folder as expected.')
                        )
                    cls._copy_dir_files(
                        src_dir=dmg_content[0],
                        dst_dir=install_dir,
                        set_progress=set_progress,
                        set_status=set_status,
                        progress_start=60,
                        progress_end=95,
                        avoid_path=avoid_path,
                    )
                    set_status(_('Unmounting DMG file...'))
                except subprocess.CalledProcessError:
                    raise SCInstallerException(_('Failed to process DMG file.'))
                finally:
                    # Always try to unmount the DMG, even if copying failed
                    try:
                        subprocess.run(
                            ['hdiutil', 'detach', str(mount_point)],
                            check=True,
                        )
                    except subprocess.CalledProcessError:
                        logger.warning(
                            'Failed to unmount DMG at [%s]', mount_point
                        )
                    # Clean up the mount point directory
                    if mount_point.exists():
                        shutil.rmtree(mount_point, ignore_errors=True)
        set_progress(100)
        set_status(_('Installation complete.'))

    @staticmethod
    def _copy_dir_files(
        src_dir: Path,
        dst_dir: Path,
        set_progress: Callable[[int], None],
        set_status: Callable[[str], None],
        progress_start: int,
        progress_end: int,
        avoid_path: Path | None = None,
    ):
        set_status(_('Copying files to [{dst}]...').format(dst=dst_dir.absolute()))
        src_files = list(src_dir.glob('**/*'))
        step = len(src_files) // (progress_end - progress_start)
        progress = progress_start
        try:
            for index, src_file in enumerate(src_files, start=1):
                if not src_file.is_file():
                    continue
                dst_file = dst_dir / src_file.relative_to(src_dir)
                if avoid_path and (
                    avoid_path == dst_file or avoid_path in dst_file.parents
                ):
                    continue
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                if index % step == 0:
                    progress += 1
                    set_progress(progress)
        except PermissionError:
            raise SCInstallerException(
                _(
                    'Error while copying files to [{path}]. Sharly Chess'
                    ' is most likely running, stop it then try again.'
                ).format(path=dst_dir.absolute())
            )
        set_progress(progress_end)

    @classmethod
    def _get_github_releases(cls) -> list[dict[str, Any]]:
        url = 'https://api.github.com/repos/sharly-chess/sharly-chess/releases'
        try:
            response = get(url, allow_redirects=True, timeout=5)
            response.raise_for_status()


            data = response.content.decode()
            return json.loads(data)
        except (RequestException, JSONDecodeError) as ex:
            logger.error('Unexpected error while requesting Github: %s', ex)
            raise SCInstallerException(
                _('An error occurred while requesting GitHub.')
            )

    @classmethod
    def _search_for_latest_version(cls, check_beta: bool) -> Version:
        """Retrieves the latest version from the GitHub repository."""

        entries = cls._get_github_releases()

        assets_by_version: dict[Version, list[dict]] = {}
        for entry in entries:
            tag_name: str = entry['tag_name']
            if matches := re.match(r'^(\d+\.\d+\.\d+)$', tag_name):
                version = Version(matches.group(1))
            elif matches := re.match(
                r'^(\d+.\d+.\d+(a\d+|b\d+|rc\d+))$',
                tag_name,
            ):
                if check_beta:
                    version = Version(matches.group(1))
                else:
                    continue
            else:
                continue
            if entry.get('draft'):
                continue
            assets_by_version[version] = entry.get('assets', [])

        return next(
            version
            for version in sorted(assets_by_version, reverse=True)
            if cls._get_asset_name(version) in [
                asset.get('name') for asset in assets_by_version[version]
            ]
        )

    @staticmethod
    def _get_asset_suffix() -> str:
        return 'windows.zip' if sys.platform == 'win32' else 'macos.dmg'

    @classmethod
    def _get_asset_name(cls, version: Version) -> str:
        """Name of the asset to download in order to install a new version."""
        return f'sharly-chess-{version}-{cls._get_asset_suffix()}'

    @classmethod
    def _get_asset_url(cls, version: Version):
        """URL of the asset to download in order to install a new version."""
        base_url = 'https://github.com/Sharly-Chess/sharly-chess/releases/download'
        asset = cls._get_asset_name(version)
        return f'{base_url}/{version}/{asset}'


