from pets import DEFAULT_PET, emotion_sequence, pet_atlas, pet_id

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

BADGE_PATH = re.compile(r"/badge/([A-Za-z0-9][A-Za-z0-9-]{0,38})")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
PAINT_ATTRIBUTES = {"fill", "stroke", "stop-color", "flood-color"}
PALETTE = {
    "#0f172a": "#242426",  # Card background
    "#1e293b": "#424245",  # Dividers and empty activity cells
    "#94a3b8": "#afafb4",  # Secondary text
    "#4ade80": "#e0e0e3",  # Cache hit rate
}
TOKEN_LABEL_BLUE = "#a6caff"
TOKEN_TOTAL_BLUE = "#79b7ff"
ACTIVITY_BLUES = {
    "#3a1e10": "#273c54",
    "#6b3a1f": "#345a80",
    "#a55733": "#477eb5",
    "#d97757": "#649cda",
    "#ffb38d": "#92c7ff",
}


def svg_tag(name):
    return f"{{{SVG}}}{name}"


def gray_color(value):
    if not HEX_COLOR.fullmatch(value):
        return value
    if value.lower() in PALETTE:
        return PALETTE[value.lower()]

    red, green, blue = (int(value[i:i + 2], 16) for i in (1, 3, 5))
    gray = round(0.2126 * red + 0.7152 * green + 0.0722 * blue)
    return "#" + f"{gray:02x}" * 3


def customize_svg(payload, pet):
    root = ET.fromstring(payload)
    if root.tag != svg_tag("svg") or root.get("viewBox") != "0 0 540 210":
        raise ValueError("Unexpected upstream Claude badge layout")

    card = root.find(svg_tag("a"))
    if card is None:
        raise ValueError("Unexpected upstream Claude badge content")
    mascot = card.find(f"{svg_tag('g')}[@shape-rendering='crispEdges']")
    original_colors = set(mascot.iter()) if mascot is not None else set()
    # The Top 5 template aligns its rank circles and digits at x=307.
    original_colors.update(card.findall(f"{svg_tag('circle')}[@cx='307']"))
    original_colors.update(card.findall(f"{svg_tag('text')}[@x='307']"))
    activity = card.find(f"{svg_tag('g')}[@transform='translate(30, 164)']")
    activity_bars = set(activity.findall(svg_tag("rect"))) if activity is not None else set()
    for element in root.iter():
        if element in original_colors:
            continue
        for attribute in PAINT_ATTRIBUTES.intersection(element.attrib):
            color = element.attrib[attribute]
            if element in activity_bars and attribute == "fill":
                element.set(attribute, ACTIVITY_BLUES.get(color.lower(), TOKEN_TOTAL_BLUE))
            else:
                element.set(attribute, gray_color(color))
        if element.get("attributeName") in PAINT_ATTRIBUTES:
            for attribute in ("values", "from", "to", "by"):
                if attribute in element.attrib:
                    element.set(attribute, ";".join(
                        gray_color(color.strip()) for color in element.attrib[attribute].split(";")
                    ))

    # The upstream template places the total and its unit on the same baseline.
    for label in card.findall(svg_tag("text")):
        if label.text in {"TOKEN 누적", "tokens", "최근 30일"}:
            label.set("fill", TOKEN_LABEL_BLUE)
        elif label.get("x") == "30" and label.get("y") == "132":
            label.set("fill", TOKEN_TOTAL_BLUE)

    # Keep the original chart coordinates together in the right column.
    width = 720
    root.set("width", str(width))
    root.set("height", "242")
    root.set("viewBox", f"0 0 {width} 242")
    background = card.find(svg_tag("rect"))
    if background is not None:
        card.remove(background)
    stats = ET.Element(svg_tag("g"), {"transform": "translate(180 0)"})
    for element in list(card):
        if element is mascot or element.tag == svg_tag("defs"):
            continue
        card.remove(element)
        stats.append(element)
    for label in stats.findall(f"{svg_tag('text')}[@x='102']"):
        label.set("x", "30")
        if (label.text or "").startswith("@"):
            label.set("font-size", "22")
            label.set("y", "42")
            # Keep long handles inside the column beside the cache statistic.
            if len(label.text) > 29:
                label.set("textLength", "360")
                label.set("lengthAdjust", "spacingAndGlyphs")
    card.append(stats)
    if mascot is not None:
        card.remove(mascot)
    name, image_uri, atlas_height = pet
    portrait = ET.SubElement(card, svg_tag("svg"), {
        "x": "1", "y": "7.5", "width": "180", "height": "195",
        "viewBox": "0 0 192 208", "overflow": "hidden",
    })
    ET.SubElement(portrait, svg_tag("title")).text = name
    image = ET.SubElement(portrait, svg_tag("image"), {
        "width": "1536", "height": str(atlas_height),
        "{http://www.w3.org/1999/xlink}href": image_uri,
    })
    frames = emotion_sequence()
    ET.SubElement(image, svg_tag("animateTransform"), {
        "attributeName": "transform", "type": "translate", "values": ";".join(frames),
        "calcMode": "discrete", "dur": f"{len(frames) * 0.16:.2f}s", "repeatCount": "indefinite",
    })

    card.set("transform", "translate(0 32)")
    root.insert(0, ET.Element(svg_tag("rect"), {
        "width": str(width), "height": "242", "rx": "12", "fill": "#242426",
    }))
    card.insert(0, ET.Element(svg_tag("path"), {
        "d": "M0 0H182V210H12Q0 210 0 198Z", "fill": "#29292c",
    }))
    card.insert(1, ET.Element(svg_tag("path"), {
        "d": "M182.5 0V210", "stroke": "#414145",
    }))
    header = ET.SubElement(root, svg_tag("g"), {"aria-hidden": "true"})
    ET.SubElement(header, svg_tag("path"), {
        "d": f"M0 32V12A12 12 0 0 1 12 0H{width - 12}A12 12 0 0 1 {width} 12V32Z",
        "fill": "#343437",
    })
    ET.SubElement(header, svg_tag("path"), {
        "d": f"M0 31.5H{width}", "stroke": "#4c4c50",
    })
    for x, color in ((18, "#ff5f57"), (34, "#febc2e"), (50, "#28c840")):
        ET.SubElement(header, svg_tag("circle"), {
            "cx": str(x), "cy": "16", "r": "5", "fill": color,
        })
    title = ET.SubElement(header, svg_tag("text"), {
        "x": str(width // 2), "y": "20", "text-anchor": "middle", "fill": "#d5d5d8",
        "font-family": "-apple-system,BlinkMacSystemFont,system-ui,sans-serif",
        "font-size": "12", "font-weight": "600",
    })
    title.text = "TokenPhage"
    return ET.tostring(root, encoding="utf-8")


def render_badge(username, pet):
    upstream = f"https://api.tokenphage.com/badge/{username}?theme=claude&mode=dark"
    request = Request(upstream, headers={
        "Accept": "image/svg+xml",
        "User-Agent": "TokenPhageBadgeProxy/1.0",
    })
    with urlopen(request, timeout=10) as response:
        return customize_svg(response.read(), pet)


class BadgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/":
            page = """<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>배지 캐릭터 선택</title>
<style>body{max-width:44rem;margin:12vh auto;padding:1rem;background:#242426;color:#eee;font:16px system-ui}label,input{display:block}input,button{box-sizing:border-box;padding:.7rem;font:inherit;border-radius:.5rem}input{width:100%;margin:.4rem 0 1rem}button{cursor:pointer}</style>
<h1>배지 캐릭터 선택</h1><form id="picker">
<label>Codex Pets 주소<input name="pet" type="url" required value="https://codex-pets.net/#/pets/umaru"></label>
<label>TokenPhage 사용자<input name="username" required value="Thrillcrazyer"></label>
<button>배지 열기</button></form>
<script>document.querySelector('form').onsubmit = event => {
  event.preventDefault();
  const data = new FormData(event.target);
  location.href = '/badge/' + encodeURIComponent(data.get('username').trim()) +
    '?' + new URLSearchParams({pet: data.get('pet').trim()});
};</script></html>""".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        match = BADGE_PATH.fullmatch(url.path)
        if not match:
            self.send_error(404)
            return
        if parse_qs(url.query).get("theme", ["claude"]) != ["claude"]:
            self.send_error(400, "Supported theme: claude")
            return

        try:
            slug = pet_id(parse_qs(url.query).get("pet", [DEFAULT_PET])[0])
        except ValueError:
            self.send_error(400, "Expected a Codex Pets page URL")
            return
        try:
            pet = pet_atlas(slug)
        except HTTPError as error:
            self.send_error(404 if error.code == 404 else 502, "Could not load Codex pet")
            return
        except (OSError, ValueError, KeyError, TypeError):
            self.send_error(502, "Could not load Codex pet")
            return

        username = match.group(1)
        try:
            svg = render_badge(username, pet)
        except HTTPError as error:
            if error.code == 404:
                self.send_error(404, "TokenPhage user not found")
            else:
                self.send_error(502, "TokenPhage unavailable")
            return
        except (URLError, TimeoutError, ET.ParseError, ValueError):
            self.send_error(502, "Could not render the TokenPhage badge")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Content-Length", str(len(svg)))
        self.end_headers()
        self.wfile.write(svg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve a graphite TokenPhage badge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), BadgeHandler) as server:
        print(f"Listening at http://{args.host}:{args.port}", flush=True)
        server.serve_forever()
