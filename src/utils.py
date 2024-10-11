# pyright: strict
from http.client import HTTPSConnection


def get_latest_bun_version() -> str:
    host = "github.com"
    conn = HTTPSConnection(host)
    try:
        conn.request("GET", "/oven-sh/bun/releases/latest", headers={"Host": host})
        response = conn.getresponse()
        location_header = response.headers["location"]
    finally:
        conn.close()

    latest_version = location_header.replace(
        "https://github.com/oven-sh/bun/releases/tag/bun-", ""
    )

    return latest_version


def convert_bun_version_into_pybun_version(
    bun_version: str, pybun_version_suffix: str = ""
) -> str:
    pybun_version = bun_version.replace("v", "")
    if pybun_version_suffix:
        pybun_version = f"{pybun_version}.{pybun_version_suffix}"

    return pybun_version
