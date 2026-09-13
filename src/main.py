import json
from typing import Any
import requests as r

from src.services.logger import get_logger
from src.config.config import Config, get_config


def get_current_version(config: Config) -> str:
    return config.get_version()


def fetch_newest_version(config: Config) -> str | None:
    repo_url = config.get_repository()
    _, _, author, repo = repo_url.split("/")
    config_url = f"https://raw.githubusercontent.com/{author}/{repo}/refs/heads/main/src/config/config.cfg"

    res = r.get(config_url, timeout=10)
    res.raise_for_status()
    fetched_config: dict[str, Any] = json.loads(res.content)

    return fetched_config["metadata"]["version"]


def update_available(local_version: str, fetched_version: str) -> bool:
    l_major, l_minor, l_patch = map(int, local_version.split("."))
    f_major, f_minor, f_patch = map(int, fetched_version.split("."))

    if f_major > l_major:
        return True
    elif f_minor > l_minor:
        return True
    elif f_patch > l_patch:
        return True
    else:
        return False


def main():
    _logger = get_logger("main")
    _config = get_config()

    _logger.info(_config.get_version(True))

    _logger.info("Running version check...")
    try:
        local_version = get_current_version(_config)
        avail_version = fetch_newest_version(_config)
    except Exception as e:
        _logger.error(f"Version check failed: {e}")


if __name__ == "__main__":
    main()
