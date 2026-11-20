import base64
from functools import lru_cache
from io import BytesIO
import json
import random
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from PIL import Image

DEFAULT_PET = "https://codex-pets.net/#/pets/umaru"


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


def emotion_sequence():
    # Idle, both runs, wave, jump, fail, wait, run, review (Codex Pets atlas order).
    counts = (6, 8, 8, 4, 5, 8, 6, 6, 6)
    states = []
    for _ in range(32):
        batch = random.sample(range(len(counts)), len(counts))
        if states and batch[0] == states[-1]:
            batch[0], batch[1] = batch[1], batch[0]
        states.extend(batch)
    if states[-1] == states[0]:
        states[-2], states[-1] = states[-1], states[-2]

    frames = []
    for row in states:
        motion = [f"{-192 * frame} {-208 * row}" for frame in range(counts[row])]
        frames.extend(motion * random.randint(2, 3))
    return frames
