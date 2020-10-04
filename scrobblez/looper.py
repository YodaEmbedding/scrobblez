from datetime import datetime, timezone
from functools import partial
from math import isclose
from time import sleep, time
from typing import Callable, Dict, Tuple

from mpris2 import Player

from scrobblez.scrobblers import Scrobbler
from scrobblez.types import Metadata, NowPlayingInfo, Scrobble

POLL_INTERVAL = 1
REL_TOL = 0.25
ABS_TOL = POLL_INTERVAL * 2


class Looper:
    def __init__(
        self,
        player: Player,
        scrobbler: Scrobbler,
        fix_metadata: Callable[[Metadata], Metadata],
    ):
        self.player: Player = player
        self.scrobbler: Scrobbler = scrobbler
        self._fix_metadata = fix_metadata
        self._metadata: Metadata = {}
        self._can_now_play: bool = False
        self._can_scrobble: bool = False
        self._elapsed: float = 0

    def run(self):
        self.scrobbler.flush_scrobble_cache()

        while True:
            loop_start = time()
            self._run_step()
            sleep(max(0, POLL_INTERVAL - (time() - loop_start)))
            if self._is_playing:
                self._elapsed += time() - loop_start

    def _run_step(self):
        metadata = clean_player_metadata(self.player.Metadata)

        if metadata != self._metadata:
            self._try_scrobble(offset=min(self._elapsed, self._duration))
            self._new_track(metadata)
        elif self._elapsed >= self._duration + 1:
            self._try_scrobble(offset=self._elapsed)
            self._new_track(metadata)
        elif not self._is_playing:
            self._try_scrobble(offset=self._elapsed)

        self._try_now_playing()

    def _new_track(self, metadata: Metadata):
        changed = metadata != self._metadata
        is_valid = metadata["duration"] > 0
        self._elapsed = 0 if changed else self._elapsed - self._duration
        self._metadata = metadata
        self._can_now_play = is_valid
        self._can_scrobble = is_valid

    def _try_now_playing(self):
        if not self._can_now_play or not self._is_playing:
            return
        self._send_now_playing()

    def _try_scrobble(self, offset: float):
        near = partial(isclose, rel_tol=REL_TOL, abs_tol=ABS_TOL)
        if not self._can_scrobble or not near(self._elapsed, self._duration):
            return
        self._send_scrobble(timestamp=int(timestamp_now() - offset))

    def _send_now_playing(self):
        info = to_now_playing(self._fix_metadata(self._metadata))
        self.scrobbler.update_now_playing(info)
        self._can_now_play = False

    def _send_scrobble(self, timestamp: int):
        scrobble = to_scrobble(self._fix_metadata(self._metadata), timestamp)
        self.scrobbler.scrobble(scrobble)
        self._can_scrobble = False

    @property
    def _duration(self) -> int:
        return self._metadata.get("duration", 1e9)

    @property
    def _is_playing(self) -> bool:
        return self.player.PlaybackStatus == "Playing"


def clean_player_metadata(m) -> Metadata:
    as_list = lambda x: list(map(str, x))
    lut: Dict[str, Tuple[str, Callable]] = {
        "album": ("xesam:album", str),
        "album_artist": ("xesam:albumArtist", as_list),
        "art_url": ("mpris:artUrl", str),
        "artist": ("xesam:artist", as_list),
        "disc_number": ("xesam:discNumber", int),
        "duration": ("mpris:length", lambda x: int(x / 1e6)),
        "title": ("xesam:title", str),
        "track_id": ("mpris:trackid", str),
        "track_number": ("xesam:trackNumber", int),
        "url": ("xesam:url", str),
    }
    return {
        k: f(m[x]) for k, (x, f) in lut.items()  # pylint: disable=not-callable
    }


def to_now_playing(metadata: Metadata) -> NowPlayingInfo:
    keep = [
        "album",
        "album_artist",
        "artist",
        "duration",
        "mbid",
        "title",
        "track_number",
    ]
    d = {k: metadata[k] for k in keep if k in metadata}
    if not all(isinstance(v, (int, str)) for v in d.values()):
        raise TypeError
    return d


def to_scrobble(metadata: Metadata, timestamp: int) -> Scrobble:
    keep = [
        "album",
        "album_artist",
        "artist",
        "duration",
        "mbid",
        "title",
        "track_number",
    ]
    d = {k: metadata[k] for k in keep if k in metadata}
    d["timestamp"] = timestamp
    if not all(isinstance(v, (int, str)) for v in d.values()):
        raise TypeError
    return d


def timestamp_now() -> float:
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()
