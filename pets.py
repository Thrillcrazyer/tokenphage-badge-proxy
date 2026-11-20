import base64
from functools import lru_cache
from io import BytesIO
import json
import random
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from PIL import Image

DEFAULT_PET = "https://codex-pets.net/#/pets/chiikawa-svg"


def pet_id(page):
    url = urlsplit(page)
    route = url.fragment or url.path
    match = re.fullmatch(r"/pets/([A-Za-z0-9_-]{1,100})/?", route)
    if url.scheme != "https" or url.netloc != "codex-pets.net" or not match:
        raise ValueError("Expected a Codex Pets page URL")
    return match[1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def download(url, limit):
    request = Request(url, headers={"User-Agent": "TokenPhageBadgeProxy/1.0"})
    with build_opener(NoRedirect()).open(request, timeout=10) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Pet asset exceeds the size limit")
    return data


@lru_cache(maxsize=32)
def pet_atlas(slug):
    metadata = json.loads(download(f"https://codex-pets.net/api/pets/{slug}", 128_000))["pet"]
    sheet_url = metadata["spritesheetUrl"]
    url = urlsplit(sheet_url)
    if url.scheme != "https" or url.netloc != "codex-pets.net" or not url.path.startswith("/assets/pets/"):
        raise ValueError("Unexpected spritesheet URL")
    data = download(sheet_url, 16_000_000)
    with Image.open(BytesIO(data)) as sheet:
        if sheet.format != "WEBP" or sheet.size not in {(1536, 1872), (1536, 2288)}:
            raise ValueError("Unsupported pet atlas")
        height = sheet.height
    uri = "data:image/webp;base64," + base64.b64encode(data).decode("ascii")
    return metadata["displayName"], uri, height


# Idle, run right, run left, wave, jump, fail, wait, run, review.
FRAME_COUNTS = (6, 8, 8, 4, 5, 8, 6, 6, 6)


def emotion_sequence():
    states = []
    for _ in range(32):
        batch = random.sample(range(len(FRAME_COUNTS)), len(FRAME_COUNTS))
        if states and batch[0] == states[-1]:
            batch[0], batch[1] = batch[1], batch[0]
        states.extend(batch)
    if states[-1] == states[0]:
        states[-2], states[-1] = states[-1], states[-2]

    frames = []
    for row in states:
        motion = [f"{-192 * frame} {-208 * row}" for frame in range(FRAME_COUNTS[row])]
        frames.extend(motion * random.randint(2, 3))
    return frames


# Phase boundaries in milliseconds: pause, run right, pause, run left.
GRASS_PHASE_MS = (0, 2400, 10800, 13200, 21600)


def grass_animation():
    trips = 10
    cycle_ms = GRASS_PHASE_MS[-1]
    values, times = [], []
    for trip in range(trips):
        left_pause, right_pause = random.sample((0, 3, 4, 5, 6, 8), 2)
        phases = zip(GRASS_PHASE_MS, GRASS_PHASE_MS[1:], (left_pause, 1, right_pause, 2))
        for start, end, row in phases:
            for frame, ms in enumerate(range(start, end, 280)):
                column = frame % FRAME_COUNTS[row]
                values.append(f"{-192 * column} {-208 * row}")
                times.append(f"{(trip * cycle_ms + ms) / (trips * cycle_ms):.8f}")
    return {"values": ";".join(values), "keyTimes": ";".join(times),
            "dur": f"{trips * cycle_ms // 1000}s"}
