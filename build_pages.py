import argparse
import os
from pathlib import Path

from pets import DEFAULT_PET, pet_atlas, pet_id
from server import BADGE_PATH, render_badge


def main():
    parser = argparse.ArgumentParser(description="Build the static TokenPhage badge site.")
    parser.add_argument("username")
    parser.add_argument("--pet", default=os.environ.get("TOKENPHAGE_PET_URL") or DEFAULT_PET)
    parser.add_argument("--output", type=Path, default=Path("_site"))
    args = parser.parse_args()
    if not BADGE_PATH.fullmatch(f"/badge/{args.username}"):
        parser.error("Expected a GitHub username")

    pet = pet_atlas(pet_id(args.pet))
    svg = render_badge(args.username, pet)
    relative_path = f"badges/{args.username}.svg"
    badge = args.output / relative_path
    badge.parent.mkdir(parents=True, exist_ok=True)
    badge.write_bytes(svg)
    grass_path = f"badges/{args.username}-grass-claude.svg"
    (args.output / grass_path).write_bytes(render_badge(args.username, pet, "grass-claude"))
    (args.output / "index.html").write_text(f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{args.username} · TokenPhage</title>
<main>
  <h1>TokenPhage badges for {args.username}</h1>
  <section>
    <h2>Usage card</h2>
    <a href="{relative_path}"><img src="{relative_path}" alt="TokenPhage usage card for {args.username}"
      style="max-width:100%;height:auto"></a>
    <p hidden><label>Profile README Markdown<br><input readonly size="80" style="max-width:95%"></label></p>
  </section>
  <section>
    <h2>Annual activity heatmap</h2>
    <a href="{grass_path}"><img src="{grass_path}" alt="Annual token activity for {args.username}"
      style="max-width:100%;height:auto"></a>
    <p hidden><label>Profile README Markdown<br><input readonly size="80" style="max-width:95%"></label></p>
  </section>
</main>
<script>
for (const section of document.querySelectorAll("section")) {{
  const image = section.querySelector("img");
  const field = section.querySelector("input");
  field.value = "![" + image.alt + "](" + image.src + ")";
  field.addEventListener("focus", () => field.select());
  field.closest("p").hidden = false;
}}
</script>
</html>
""", encoding="utf-8")


if __name__ == "__main__":
    main()
