"""
Driver factory — the one place that knows how to turn a platform key
into a connected, ready-to-use GraphDriver instance.
"""

from src.config import PLATFORMS, get_connection_info
from src.drivers.cypher_driver import CypherDriver
from src.drivers.falkordb_driver import FalkorDriver
from src.drivers.arangodb_driver import ArangoDriver


def get_driver(platform_key: str):
    if platform_key not in PLATFORMS:
        raise ValueError(f"Unknown platform key: {platform_key}. Known: {list(PLATFORMS.keys())}")

    conn = get_connection_info(platform_key)

    if platform_key in ("cognodb", "aura"):
        driver = CypherDriver(
            uri=conn["uri"],
            user=conn["user"],
            password=conn["password"],
            platform_label=platform_key,
        )
    elif platform_key == "falkordb":
        driver = FalkorDriver(
            host=conn["host"],
            port=conn["port"],
        )
    elif platform_key == "arangodb":
        driver = ArangoDriver(
            uri=conn["uri"],
            user=conn["user"],
            password=conn["password"],
            db_name=conn["db_name"],
        )
    else:
        raise ValueError(f"No driver mapping defined for platform key: {platform_key}")

    driver.connect()
    return driver


if __name__ == "__main__":
    for key in PLATFORMS:
        print(f"Connecting to {key} ...")
        driver = get_driver(key)
        print(f"  OK — {PLATFORMS[key].display_name} connected via factory.")
        driver.close()
    print("\nAll platforms connect successfully via the driver factory.")
