import json
import os
from datetime import datetime, timezone
from typing import Iterator, List

import pylast
from xdg.BaseDirectory import xdg_cache_home

from scrobblez.types import NowPlayingInfo, Scrobble

CACHE_ROOT = os.path.join(xdg_cache_home, "scrobblez")
UNSCROBBLED_DB_PATH = os.path.join(CACHE_ROOT, "unscrobbled.db")
HISTORY_DB_PATH = os.path.join(CACHE_ROOT, "history.db")

os.makedirs(CACHE_ROOT, exist_ok=True)


class Scrobbler:
    def scrobble(self, scrobble: Scrobble):
        raise NotImplementedError

    def update_now_playing(self, info: NowPlayingInfo):
        raise NotImplementedError

    def flush_scrobble_cache(self):
        raise NotImplementedError


class LastFMScrobbler(Scrobbler):
    def __init__(
        self, network: pylast.LastFMNetwork, cache_only: bool = False
    ):
        self.network = network
        self.cache = ScrobbleQueue(UNSCROBBLED_DB_PATH)
        self._log_queue = ScrobbleQueue(HISTORY_DB_PATH)
        self.cache_only = cache_only

    def scrobble(self, scrobble: Scrobble):
        log("Scrobble", fmt_dict(scrobble))
        self.cache.put(scrobble)
        self._log_queue.put(scrobble)
        self.flush_scrobble_cache()

    def update_now_playing(self, info: NowPlayingInfo):
        log("Now playing", fmt_dict(info))
        self.network.update_now_playing(**info)

    def flush_scrobble_cache(self):
        """Send scrobbles over network."""
        if self.cache_only:
            return

        while not self.cache.empty():
            try:
                scrobbles = self.cache.peek_n(50)
                scrobbles_str = "\n".join(map(json.dumps, scrobbles))
                self.network.scrobble_many(scrobbles)
                log("Sent scrobbles", scrobbles_str)
            except Exception as e:
                log("Exception when sending scrobbles", f"{type(e)}({e})")
                return
            self.cache.pop_n(50)


class ScrobbleQueue:
    _queue: List[Scrobble]

    def __init__(self, db_path):
        self._db_path = db_path
        self._queue = list(self._read_db())

    def __len__(self):
        return len(self._queue)

    def empty(self):
        return len(self) == 0

    def put(self, scrobble: Scrobble):
        self._queue.append(scrobble)
        self._append_db(scrobble)

    def peek_n(self, n):
        return self._queue[:n]

    def pop_n(self, n):
        items = self._queue[:n]
        self._queue = self._queue[n:]
        self._write_db()
        return items

    def _append_db(self, scrobble):
        with open(self._db_path, "a") as f:
            line = json.dumps(scrobble)
            f.write(f"{line}\n")

    def _write_db(self):
        with open(self._db_path, "w") as f:
            for scrobble in self._queue:
                line = json.dumps(scrobble)
                f.write(f"{line}\n")

    def _read_db(self) -> Iterator[Scrobble]:
        try:
            with open(self._db_path) as f:
                for line in f:
                    yield json.loads(line)
        except FileNotFoundError:
            return


def log(tag, msg):
    print(f"{datestr_now()}\n{tag}:\n{msg}\n")


def datestr_now() -> str:
    return (
        datetime.utcnow()
        .replace(tzinfo=timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )


def fmt_dict(d: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in d.items())
