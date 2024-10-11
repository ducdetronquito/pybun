# pyright: basic
import logging
import os
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib import request
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from utils import convert_bun_version_into_pybun_version, get_latest_bun_version

from wheel.wheelfile import WheelFile

if TYPE_CHECKING:
    from wheel.wheelfile import SizedBuffer


logger = logging.getLogger("pybun")


class ReproducibleWheelFile(WheelFile):
    def writestr(
        self,
        zinfo_or_arcname: str | ZipInfo,
        data: "SizedBuffer | str",
        *args: Any,
        **kwargs: Any,
    ):
        if isinstance(zinfo_or_arcname, ZipInfo):
            zinfo = zinfo_or_arcname
        else:
            zinfo = ZipInfo(zinfo_or_arcname)
            zinfo.file_size = len(data)
            zinfo.external_attr = 0o0644 << 16
            if zinfo_or_arcname.endswith(".dist-info/RECORD"):
                zinfo.external_attr = 0o0664 << 16

        zinfo.compress_type = ZIP_DEFLATED
        zinfo.date_time = (1980, 1, 1, 0, 0, 0)
        zinfo.create_system = 3
        super().writestr(zinfo, data, *args, **kwargs)


type BunTargetPlatform = (
    Literal["darwin-x64"]
    | Literal["darwin-aarch64"]
    | Literal["linux-aarch64"]
    | Literal["linux-x64"]
    | Literal["windows-x64"]
)


def parse_bun_target_platform(value: str) -> BunTargetPlatform | None:
    match value:
        case "darwin-x64":
            return value
        case "darwin-aarch64":
            return value
        case "linux-aarch64":
            return value
        case "linux-x64":
            return value
        case "windows-x64":
            return value
        case _:
            return None


def all_bun_target_platforms() -> list[BunTargetPlatform]:
    return ["darwin-x64", "darwin-aarch64", "linux-aarch64", "linux-x64", "windows-x64"]


type PythonTargetPlatform = (
    Literal["macosx_12_0_arm64"]
    | Literal["macosx_12_0_x86_64"]
    | Literal["manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64"]
    | Literal["manylinux_2_12_x86_64.manylinux2010_x86_64.musllinux_1_1_x86_64"]
    | Literal["win_amd64"]
)


def get_maching_python_target_platform(
    bun_target_platform: BunTargetPlatform,
) -> PythonTargetPlatform:
    match bun_target_platform:
        case "darwin-x64":
            return "macosx_12_0_x86_64"
        case "darwin-aarch64":
            return "macosx_12_0_arm64"
        case "linux-aarch64":
            return "manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64"
        case "linux-x64":
            return "manylinux_2_12_x86_64.manylinux2010_x86_64.musllinux_1_1_x86_64"
        case "windows-x64":
            return "win_amd64"


@dataclass(frozen=True, slots=True)
class DistInfo:
    name: str
    version: str

    def path(self) -> str:
        return f"{self.name}-{self.version}.dist-info"


@dataclass(frozen=True, slots=True)
class DistInfoMetadata:
    dist_info: DistInfo
    bun_version: str

    def path(self) -> str:
        return f"{self.dist_info.path()}/METADATA"

    def content(self) -> bytes:
        with open("README.md") as f:
            description = f.read()

        rows = [
            "Metadata-Version: 2.3",
            f"Name: {self.dist_info.name}",
            f"Version: {self.dist_info.version}",
            "Summary: Bun is an all-in-one toolkit for JavaScript and TypeScript apps.",
            "Description-Content-Type: text/markdown",
            "License: MIT",
            "Classifier: License :: OSI Approved :: MIT License",
            "Project-URL: Homepage, https://bun.sh/",
            "Project-URL: Source Code, https://github.com/oven-sh/bun",
            "Project-URL: Bug Tracker, https://github.com/oven-sh/bun/issues",
            f"Project-URL: Changelog, https://bun.sh/blog/bun-{self.bun_version}",
            "Project-URL: Documentation, https://bun.sh/docs",
            "Requires-Python: ~=3.9",
            "",
            description,
        ]

        return "\n".join(rows).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DistInfoWheel:
    dist_info: DistInfo
    wheel_tag: str

    def path(self) -> str:
        return f"{self.dist_info.path()}/WHEEL"

    def content(self) -> bytes:
        rows = [
            "Wheel-Version: 1.0",
            "Generator: pybun src/make_wheels.py",
            "Root-Is-Purelib: false",
            f"Tag: {self.wheel_tag}",
        ]
        return "\n".join(rows).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DistInfoEntrypoints:
    dist_info: DistInfo

    def path(self) -> str:
        return f"{self.dist_info.path()}/entry_points.txt"

    def content(self) -> bytes:
        with open("assets/entry_points.txt", mode="rb") as file:
            entry_points = file.read()

        return entry_points


@dataclass(frozen=True, slots=True)
class BunExecutable:
    file_info: ZipInfo
    content: bytes

    @classmethod
    def from_archive(
        cls, release_archive: bytes, bun_target_platform: BunTargetPlatform
    ) -> "BunExecutable":
        match bun_target_platform:
            case "windows-x64":
                executable_name = "bun.exe"
            case _:
                executable_name = "bun"

        with ZipFile(BytesIO(release_archive)) as zip_file:
            archive_executable_path = f"bun-{bun_target_platform}/{executable_name}"

            with zip_file.open(archive_executable_path) as bun_executable:
                mode = zip_file.getinfo(archive_executable_path).external_attr >> 16
                mode = (mode & 0xFFFF) << 16
                file_info = ZipInfo(f"pybun/{executable_name}")
                file_info.external_attr = mode
                return BunExecutable(file_info=file_info, content=bun_executable.read())


@dataclass(frozen=True, slots=True)
class Wheel:
    pybun_version: str
    bun_version: str
    python_target_platform: PythonTargetPlatform
    name = "pybun"

    def filename(self) -> str:
        return f"{self.name}-{self.pybun_version}-{self.get_tag()}.whl"

    def get_tag(self) -> str:
        return f"py3-none-{self.python_target_platform}"

    def write(self, bun_executable: BunExecutable, output_dir: str) -> str:
        Path(output_dir).mkdir(exist_ok=True)

        dist_info = DistInfo(self.name, self.pybun_version)
        dist_info_metadata = DistInfoMetadata(dist_info, self.bun_version)
        dist_info_wheel = DistInfoWheel(dist_info, self.get_tag())
        dist_info_entrypoints = DistInfoEntrypoints(dist_info)

        with open("assets/__main__.py", mode="rb") as file:
            pybun_main = file.read()

        files: list[tuple[str | ZipInfo, bytes]] = [
            (dist_info_metadata.path(), dist_info_metadata.content()),
            (dist_info_wheel.path(), dist_info_wheel.content()),
            (dist_info_entrypoints.path(), dist_info_entrypoints.content()),
            ("pybun/__init__.py", b"\n"),
            ("pybun/__main__.py", pybun_main),
            (bun_executable.file_info, bun_executable.content),
        ]

        wheel_path = os.path.join(output_dir, self.filename())
        with ReproducibleWheelFile(wheel_path, "w") as wheel:
            for file_path, content in files:
                wheel.writestr(file_path, content)
        return wheel_path


def get_release_url(bun_version: str, bun_target_platform: BunTargetPlatform) -> str:
    return f"https://github.com/oven-sh/bun/releases/download/bun-{bun_version}/bun-{bun_target_platform}.zip"


def get_release_hashes_url(bun_version: str) -> str:
    return f"https://github.com/oven-sh/bun/releases/download/bun-{bun_version}/SHASUMS256.txt"


def get_cli_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog=__file__, description="Repackage official Bun binaries as Python wheels"
    )
    parser.add_argument(
        "bun_version",
        help="Bun version to package",
    )
    parser.add_argument(
        "--platform",
        choices=all_bun_target_platforms(),
        action="append",
        default=[],
        help="platform to build for, can be repeated to target multiple platform. If omitted all platform are targeted.",
    )
    parser.add_argument(
        "--pybun-version-suffix",
        default="",
        help="Ex: alpha1, alpha2, post1, etc...",
    )

    return parser


def get_release_hashes(bun_version: str) -> dict[BunTargetPlatform, str]:
    release_hashes_url = get_release_hashes_url(bun_version)
    logger.info(f"Fetching release hashes for {bun_version}")

    result = {}

    with request.urlopen(release_hashes_url) as response:
        hash_lines: list[str] = response.read().decode("utf-8").splitlines()

    for hash_line in hash_lines:
        hash, release_archive_name = hash_line.split("  ")
        platform = release_archive_name.replace("bun-", "").replace(".zip", "")
        if "profile" in platform:
            continue

        bun_target_platform = parse_bun_target_platform(platform)
        if bun_target_platform is None:
            continue

        result[bun_target_platform] = hash

    return result


def get_release_archive(
    bun_version: str, bun_target_platform: BunTargetPlatform
) -> bytes:
    release_url = get_release_url(bun_version, bun_target_platform)

    logger.info(
        f"Fetching release {bun_version} hash for platform {bun_target_platform}"
    )
    with request.urlopen(release_url) as response:
        logger.info(f"Request to {release_url}")
        release_archive: bytes = response.read()

    return release_archive


def build_wheel(
    bun_target_platform: BunTargetPlatform,
    bun_version: str,
    pybun_version: str,
    expected_release_hash: str,
) -> None:
    release_archive = get_release_archive(bun_version, bun_target_platform)

    release_hash = sha256(release_archive).hexdigest()
    if release_hash != expected_release_hash:
        logger.error(
            f"Release {bun_version} hash mismatch for platform {bun_target_platform}: expected={expected_release_hash}, found={release_hash}"
        )
        return sys.exit(1)

    logger.info(
        f"Release {bun_version} hash for platform {bun_target_platform} is {release_hash}"
    )

    bun_executable = BunExecutable.from_archive(release_archive, bun_target_platform)

    python_target_platform = get_maching_python_target_platform(bun_target_platform)
    wheel_path = Wheel(pybun_version, bun_version, python_target_platform).write(
        bun_executable, "dist/"
    )

    logger.info(f"Wheel has been generated: {wheel_path}")


def parse_expected_target_platforms(platforms: list[str]) -> list[BunTargetPlatform]:
    if not platforms:
        return all_bun_target_platforms()

    bun_target_platforms = list[BunTargetPlatform]()
    for item in platforms:
        bun_target_platform = parse_bun_target_platform(item)
        if bun_target_platform is None:
            logger.error(f"Bun target platform '{item}' does not exists")
            return sys.exit(1)

        bun_target_platforms.append(bun_target_platform)

    return bun_target_platforms


def main():
    logging.getLogger("wheel").setLevel(logging.WARNING)

    cli_args = get_cli_arg_parser().parse_args()

    bun_version: str = cli_args.bun_version

    if bun_version == "latest":
        bun_version = get_latest_bun_version()

    pybun_version_suffix: str = cli_args.pybun_version_suffix

    bun_target_platforms = parse_expected_target_platforms(cli_args.platform)

    release_hashes = get_release_hashes(bun_version)

    pybun_version = convert_bun_version_into_pybun_version(
        bun_version, pybun_version_suffix
    )

    for bun_target_platform in bun_target_platforms:
        expected_release_hash = release_hashes[bun_target_platform]

        build_wheel(
            bun_target_platform=bun_target_platform,
            bun_version=bun_version,
            pybun_version=pybun_version,
            expected_release_hash=expected_release_hash,
        )


if __name__ == "__main__":
    main()
