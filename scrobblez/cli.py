import argparse
import json
import os
from itertools import count
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
CONFIG_PATH = os.path.join(CONFIG_ROOT, "config.py")
SECRET_PATH = os.path.join(CONFIG_ROOT, "secret.json")
URI_POLL_INTERVAL = 1
URI_PREFIX = "org.mpris.MediaPlayer2."


os.makedirs(CONFIG_ROOT, exist_ok=True)

MetadataFixer = Callable[[Metadata], Metadata]


def get_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--cache-only", action="store_true")
    return parser.parse_args()


def cli_run(fix_metadata: MetadataFixer, whitelist: List[str]):
    args = get_args()

    if whitelist == []:
        whitelist = _configure_whitelist()

    network = _get_lastfm_network()
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


def _get_lastfm_network() -> pylast.LastFMNetwork:
    try:
        with open(SECRET_PATH) as f:
            secret = json.load(f)
    except FileNotFoundError:
        api_key_url = "https://www.last.fm/api/account/create"
        print(
            f"Please visit the following link to obtain credentials:\n"
            f"{api_key_url}\n\n"
            f"These credentials and an MD5 hash of your password will be "
            f"stored within:\n"
            f"{SECRET_PATH}\n"
        )

        prefix = "Please enter your"
        prompts = {
            "api_key": "API key",
            "api_secret": "API secret",
            "username": "username",
            "password": "password",
        }
        secret = {k: input(f"{prefix} {v}: ") for k, v in prompts.items()}
        secret["password_hash"] = pylast.md5(secret["password"])
        del secret["password"]
        print("")

        with open(SECRET_PATH, "w") as f:
            json.dump(secret, f, indent=4)
            f.write("\n")

    return pylast.LastFMNetwork(**secret)


def _configure_whitelist() -> List[str]:
    names = [_removeprefix(uri, URI_PREFIX) for uri in get_players_uri()]
    available = "\n".join(f"{i}. {x}" for i, x in enumerate(names, start=1))
    print(f"Currently available players:\n{available}\n")
    print("Please provide a whitelist of valid players:")
    whitelist = []

    for i in count(start=1):
        entry = input(f"{i}. ")
        if entry == "":
            break
        whitelist.append(entry)

    print("")

    if whitelist != []:
        with open(CONFIG_PATH, "a") as f:
            f.write(f"\nwhitelist = {json.dumps(whitelist, indent=4)}\n")
        print(f"Configuration saved to:\n{CONFIG_PATH}\n")

    return whitelist


def _get_valid_player_uri(whitelist: List[str]) -> str:
    while True:
        uri = _get_player_uri(whitelist)
        if uri is not None:
            return uri
        sleep(URI_POLL_INTERVAL)


def _get_player_uri(whitelist: List[str]) -> Optional[str]:
    for uri in get_players_uri():
        name = _removeprefix(uri, URI_PREFIX)
        if any(_matches_rule(r, name) for r in whitelist):
            return uri

    return None


def _matches_rule(rule: str, name: str) -> bool:
    if "*" not in rule:
        return name in rule
    raise NotImplementedError("Globbing not yet implemented.")


def _removeprefix(s: str, prefix: str) -> str:
    return s[len(prefix) :] if s[: len(prefix)] == prefix else s
