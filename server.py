from pets import DEFAULT_PET, GRASS_PHASE_MS, emotion_sequence, grass_animation, pet_atlas, pet_id

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
BADGE_FONT = "'SF Mono',SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
PURPLE = "#D08BF5"
TOKEN_WHITE = "#ffffff"
ACTIVITY_GRAYS = {
    "#3a1e10": "#646464",
    "#6b3a1f": "#898989",
    "#a55733": "#adadad",
    "#d97757": "#d5d5d5",
    "#ffb38d": "#ffffff",
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
    # Top 5 heading, ranks, names, and totals use the upstream column colors.
    original_colors.update(card.findall(f"{svg_tag('circle')}[@cx='307']"))
    original_colors.update(label for label in card.findall(svg_tag("text"))
                           if label.get("x") in {"300", "307", "321", "520"})
    activity = card.find(f"{svg_tag('g')}[@transform='translate(30, 164)']")
    activity_bars = set(activity.findall(svg_tag("rect"))) if activity is not None else set()
    for element in root.iter():
        if element in original_colors:
            continue
        for attribute in PAINT_ATTRIBUTES.intersection(element.attrib):
            color = element.attrib[attribute]
            if element in activity_bars and attribute == "fill":
                element.set(attribute, ACTIVITY_GRAYS.get(color.lower(), TOKEN_WHITE))
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
        if label.text == "TOKEN 누적":
            label.text = "Total tokens"
        elif label.text == "최근 30일":
            label.text = "Last 30 days"
        elif label.get("x") == "102" and label.get("y") == "62":
            book = re.fullmatch(r"(.+) ([0-9.,]+)권 .+", label.text or "")
            if book:
                label.text = f"Devouring {book[2]} × {book[1]}"
        if label.text in {"Total tokens", "tokens", "Last 30 days"}:
            label.set("fill", "#ffffff")
        elif label.get("x") == "30" and label.get("y") == "132":
            label.set("fill", TOKEN_WHITE)

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
    card.insert(0, ET.Element(svg_tag("path"), {
        "d": "M0 0H182V210H12Q0 210 0 198Z", "fill": "#29292c",
    }))
    card.insert(1, ET.Element(svg_tag("path"), {
        "d": "M182.5 0V210", "stroke": "#414145",
    }))
    add_pet(card, pet, 19, 27, 144, 156)
    return finish_card(root, card, width, original_colors)


def customize_grass(payload, pet):
    root = ET.fromstring(payload)
    card = root.find(svg_tag("a"))
    if root.get("viewBox") != "0 0 700 190" or card is None:
        raise ValueError("Unexpected upstream grass badge layout")

    width = 700
    root.set("height", "222")
    root.set("viewBox", "0 0 700 222")
    levels = {
        "#1c2536": "#35313b", "#5a2f1e": "#503454", "#8a3a1f": "#71477e",
        "#c05a30": "#955cab", "#e58a5f": "#b977d2", "#f6c9a8": PURPLE,
    }
    for child in list(card):
        if child.tag == svg_tag("rect") and child.get("width") == "699":
            card.remove(child)
            continue
        if child.find(f"{svg_tag('g')}[@shape-rendering='crispEdges']") is not None and child.get("transform") is None:
            card.remove(child)
            continue  # Original mascot layer
        if child.get("width") == "9" and child.get("height") == "9":
            fill = child.get("fill")
            child.set("fill", levels.get(fill, fill))
        if child.get("aria-label", "").endswith("tokens/year"):
            for pixel in child.findall(svg_tag("rect")):
                pixel.set("fill", PURPLE)
    scene = card.find(f"{svg_tag('g')}[@clip-path]")
    if scene is None:
        raise ValueError("Missing grass scenery")
    walker = ET.SubElement(scene, svg_tag("g"))
    ET.SubElement(walker, svg_tag("animateTransform"), {
        "attributeName": "transform", "type": "translate",
        "values": "0 0;0 0;265 0;265 0;0 0",
        "keyTimes": ";".join(f"{ms / GRASS_PHASE_MS[-1]:.8f}" for ms in GRASS_PHASE_MS),
        "dur": f"{GRASS_PHASE_MS[-1]}ms", "repeatCount": "indefinite",
    })
    add_pet(walker, pet, 334, 12, 48, 52, grass_animation())
    return finish_card(root, card, width, set())


def add_pet(parent, pet, x, y, width, height, animation=None):
    name, image_uri, atlas_height = pet
    portrait = ET.SubElement(parent, svg_tag("svg"), {
        "x": str(x), "y": str(y), "width": str(width), "height": str(height),
        "viewBox": "0 0 192 208", "overflow": "hidden",
    })
    ET.SubElement(portrait, svg_tag("title")).text = name
    image = ET.SubElement(portrait, svg_tag("image"), {
        "width": "1536", "height": str(atlas_height),
        "{http://www.w3.org/1999/xlink}href": image_uri,
    })
    if animation is None:
        frames = emotion_sequence()
        animation = {"values": ";".join(frames), "dur": f"{len(frames) * 0.28:.2f}s"}
    ET.SubElement(image, svg_tag("animateTransform"), {
        "attributeName": "transform", "type": "translate", "calcMode": "discrete",
        "repeatCount": "indefinite", **animation,
    })


def finish_card(root, card, width, original_colors):
    card.set("transform", "translate(0 32)")
    root.insert(0, ET.Element(svg_tag("rect"), {
        "width": str(width), "height": root.get("height"), "rx": "12", "fill": "#242426",
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
        "font-size": "12", "font-weight": "600",
    })
    title.text = "TokenPhage"
    for label in root.iter(svg_tag("text")):
        label.set("font-family", BADGE_FONT)
        if label in original_colors:
            continue
        parts = re.split(r"(@|[0-9]+(?:[.,][0-9]+)*)", label.text or "")
        label.text = parts[0]
        for accent, rest in zip(parts[1::2], parts[2::2]):
            span = ET.SubElement(label, svg_tag("tspan"), {"fill": PURPLE})
            span.text = accent
            span.tail = rest
    return ET.tostring(root, encoding="utf-8")


def render_badge(username, pet, theme="claude"):
    upstream = f"https://api.tokenphage.com/badge/{username}?theme={theme}&mode=dark"
    request = Request(upstream, headers={
        "Accept": "image/svg+xml",
        "User-Agent": "TokenPhageBadgeProxy/1.0",
    })
    with urlopen(request, timeout=10) as response:
        render = customize_grass if theme == "grass-claude" else customize_svg
        return render(response.read(), pet)


class BadgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/":
            page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Choose a badge character</title>
<style>body{max-width:44rem;margin:12vh auto;padding:1rem;background:#242426;color:#eee;font:16px system-ui}label,input{display:block}input,button{box-sizing:border-box;padding:.7rem;font:inherit;border-radius:.5rem}input{width:100%;margin:.4rem 0 1rem}button{cursor:pointer}</style>
<h1>Choose a badge character</h1><form id="picker">
<label>Codex Pets URL<input name="pet" type="url" required value="https://codex-pets.net/#/pets/chiikawa-svg"></label>
<label>TokenPhage username<input name="username" required placeholder="Your GitHub username"></label>
<label>Theme <select name="theme"><option>claude</option><option>grass-claude</option></select></label>
<button>Open badge</button></form>
<script>document.querySelector('form').onsubmit = event => {
  event.preventDefault();
  const data = new FormData(event.target);
  location.href = '/badge/' + encodeURIComponent(data.get('username').trim()) +
    '?' + new URLSearchParams({pet: data.get('pet').trim(), theme: data.get('theme')});
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
        theme = parse_qs(url.query).get("theme", ["claude"])[0]
        if theme not in {"claude", "grass-claude"}:
            self.send_error(400, "Supported themes: claude, grass-claude")
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
            svg = render_badge(username, pet, theme)
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
