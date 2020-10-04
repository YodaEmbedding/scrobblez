import importlib.util
import os
from contextlib import suppress

from metadata_filter import *
from xdg.BaseDirectory import xdg_config_home

from scrobblez.cli import cli_run
from scrobblez.types import Metadata

CONFIG_ROOT = os.path.join(xdg_config_home, "scrobblez")
CONFIG_PATH = os.path.join(CONFIG_ROOT, "config.py")


def default_fix_metadata(metadata: Metadata) -> Metadata:
    m = dict(metadata)

    rules = (
        REMASTERED_FILTER_RULES
        + SUFFIX_FILTER_RULES
        + VERSION_FILTER_RULES
        + ORIGIN_FILTER_RULES
        + FEATURE_FILTER_RULES
        + CLEAN_EXPLICIT_FILTER_RULES
        + LIVE_FILTER_RULES
        + TRIM_WHITESPACE_FILTER_RULES
    )

    m["title"] = apply_filters(rules, m["title"])
    m["album"] = apply_filters(rules, m["album"])
    m["artist"] = m["artist"][0]
    m["album_artist"] = m["album_artist"][0]

    return m


def path_import(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    fix_metadata = default_fix_metadata
    whitelist = []

    with suppress(FileNotFoundError):
        config = path_import("config", CONFIG_PATH)

        if hasattr(config, "fix_metadata"):
            fix_metadata = config.fix_metadata

        if hasattr(config, "whitelist"):
            whitelist = config.whitelist

    cli_run(fix_metadata, whitelist)


if __name__ == "__main__":
    main()
