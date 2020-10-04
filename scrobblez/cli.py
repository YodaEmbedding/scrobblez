import argparse
import json
import os
from time import sleep
from typing import Callable, List, Optional

import dbus
import pylast
from mpris2 import Player, get_players_uri
from xdg.BaseDirectory import xdg_config_home

from scrobblez.looper import Looper
from scrobblez.scrobblers import LastFMScrobbler, Scrobbler
from scrobblez.types import Metadata

CONFIG_ROOT = os.path.join(xdg_config_home, "scrobblez")
SECRET_PATH = os.path.join(CONFIG_ROOT, "secret.json")
URI_POLL_INTERVAL = 1

MetadataFixer = Callable[[Metadata], Metadata]


def get_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--cache-only", action="store_true")
    return parser.parse_args()


def cli_run(fix_metadata: MetadataFixer, whitelist: List[str]):
    args = get_args()

    with open(SECRET_PATH) as f:
        secret_config = json.load(f)

    network = pylast.LastFMNetwork(**secret_config)
    scrobbler = LastFMScrobbler(network, cache_only=args.cache_only)

    while True:
        try:
            _run_loop(fix_metadata, whitelist, scrobbler)
        except dbus.exceptions.DBusException as e:
            print(f"Player disconnected\n{e}\n")


def _run_loop(
    fix_metadata: MetadataFixer, whitelist: List[str], scrobbler: Scrobbler
):
    uri = _get_valid_player_uri(whitelist)
    print(f"Found player {uri}")
    player = Player(  # pylint: disable=unexpected-keyword-arg
        dbus_interface_info={"dbus_uri": uri}
    )
    print(f"Listening to player {uri}\n")
    scrobble_loop = Looper(player, scrobbler, fix_metadata)
    scrobble_loop.run()


def _get_valid_player_uri(whitelist: List[str]) -> str:
    while True:
        uri = _get_player_uri(whitelist)
        if uri is not None:
            return uri
        sleep(URI_POLL_INTERVAL)


def _get_player_uri(whitelist: List[str]) -> Optional[str]:
    prefix = "org.mpris.MediaPlayer2."

    for uri in get_players_uri():
        name = _removeprefix(uri, prefix)
        if any(_matches_rule(r, name) for r in whitelist):
            return uri

    return None


def _matches_rule(rule: str, name: str) -> bool:
    if "*" not in rule:
        return name in rule
    raise NotImplementedError("Globbing not yet implemented.")


def _removeprefix(s: str, prefix: str) -> str:
    return s[len(prefix) :] if s[: len(prefix)] == prefix else s