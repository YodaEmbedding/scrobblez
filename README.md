# scrobblez

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

User-customizable scrobbler for Last.fm and MPRIS 2.

This scrobbler cleans up metadata (e.g. artist, album, track titles) produced
by services with non-standard tagging schemes (e.g. Spotify). The cleaning
process is extensible and can be customized to a user's particular needs.

## Install

Install from PyPI:

```bash
pip install scrobblez
```

Or install from source:

```bash
git clone https://github.com/YodaEmbedding/scrobblez
cd scrobblez
pip install .
```

## Usage

Simply run the following command:

```bash
scrobblez
```

## Configuration

Within `~/.config/scrobblez/config.py`, you may specify a whitelist of valid
player names:

```python
whitelist = ["spotify"]
```

Optionally, you can also customize the metadata cleaning process:

```python
from scrobblez.metadata_filter import *
from scrobblez.types import Metadata

def fix_metadata(metadata: Metadata) -> Metadata:
    m = dict(metadata)

    # Keep first artist only in list of artists
    m["artist"] = m["artist"][0]
    m["album_artist"] = m["album_artist"][0]

    # Specify which filter rules to use
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

    # Specify manual artist/album/title overrides
    artist_overrides = {
        "Yusuf": "Cat Stevens",
        "Yusuf / Cat Stevens": "Cat Stevens",
    }

    album_overrides = {
        "The Lord of the Rings - The Return of the King - "
        "The Complete Recordings (Limited Edition)":
        "The Lord of the Rings: Return of the King - the Complete Recordings",
    }

    title_overrides = {
        "Better Get Hit In Your Soul - Instrumental":
        "Better Git It in Your Soul",
    }

    def fix(k, overrides, f=lambda x: x):
        m[k] = overrides.get(m[k], f(m[k]))

    # Apply fixes
    fix("artist", artist_overrides)
    fix("album_artist", artist_overrides)
    fix("album", album_overrides, lambda x: apply_filters(rules, x))
    fix("title", title_overrides, lambda x: apply_filters(rules, x))

    return m
```
