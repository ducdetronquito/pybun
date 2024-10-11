from io import BytesIO
import logging
import sys
from utils import convert_bun_version_into_pybun_version, get_latest_bun_version
from http.client import HTTPSConnection
import xml.etree.ElementTree as std_xml


logger = logging.getLogger("pybun")


def get_latest_pybun_version() -> str:
    host = "pypi.org"
    conn = HTTPSConnection(host)
    try:
        conn.request("GET", "/rss/project/pybun/releases.xml", headers={"Host": host})
        response = conn.getresponse()
        assert response.status == 200
        content = response.read()
    finally:
        conn.close()

    tree = std_xml.parse(BytesIO(content))
    latest_pybun_version = tree.getroot().find("channel/item/title").text
    return latest_pybun_version


def main():
    latest_bun_version = get_latest_bun_version()
    logger.info(f"Latest bun version released is {latest_bun_version}")

    latest_pybun_version = get_latest_pybun_version()
    logger.info(f"Latest pybun version released is {latest_pybun_version}")

    expected_latest_pybun_version = convert_bun_version_into_pybun_version(
        latest_bun_version
    )

    if latest_pybun_version.startswith(expected_latest_pybun_version):
        logger.info(
            "Latest pybun version match the latest bun version: nothing to release."
        )
        return

    logger.info(
        "Latest pybun version does not match the latest bun version: a new pybun release is required."
    )

    with open("LATEST_UNRELEASED_BUN_VERSION.txt", "w") as f:
        f.write(latest_bun_version)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    main()
