# TokenPhage Badge Proxy

Show your TokenPhage usage in your GitHub profile README with two animated badges hosted on your own GitHub Pages site. This project fetches your badge SVGs from the official TokenPhage API and customizes their colors, typography, and layout with a Codex Pets character. TokenPhage supplies the usage figures and model rankings. [Original TokenPhage badges](https://github.com/TOKENPHAGE/tokenphage-api)

## Preview

**Usage card** (`claude`) shows your total tokens, cache hit rate, usage over the last 30 days, and top five models.

![Example usage card with an animated character beside the token statistics](docs/previews/claude.svg)

**Annual activity heatmap** (`grass-claude`) shows a year of daily token usage. Brighter green squares indicate higher usage.

![Example annual activity badge with Duodong walking above a green heatmap](docs/previews/grass-claude.svg)

Both examples feature the default character, Duodong (多栋), a beagle by froggie. [Duodong on Codex Pets](https://codex-pets.net/#/pets/duodong)

## Publish your badges on GitHub Pages

1. Sync your usage to TokenPhage with your GitHub username. [TokenPhage CLI guide](https://github.com/TOKENPHAGE/tokenphage-cli)
2. Fork this repository into your GitHub account. In your fork, open **Actions** and enable workflows.
3. Under **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**.
4. Open **Actions → Publish TokenPhage badge → Run workflow** and run it on `main`. The workflow uses the fork owner's GitHub username by default.
5. When the deployment finishes, open the **github-pages** deployment URL. Copy the **Profile README Markdown** beneath either badge and paste it into your profile `README.md`.

The workflow refreshes both SVGs every six hours and after pushes to `main`. Each badge keeps its URL across refreshes. For a project site on the default GitHub Pages domain, use these link formats.

```markdown
![TokenPhage usage card](https://OWNER.github.io/REPOSITORY/badges/USERNAME.svg)
![TokenPhage annual activity](https://OWNER.github.io/REPOSITORY/badges/USERNAME-grass-claude.svg)
```

`OWNER` and `REPOSITORY` identify the fork. `USERNAME` is the TokenPhage account used for the build. The Markdown on your deployed site already includes the correct domain, path, and filename.

## Customize your fork

Under **Settings → Secrets and variables → Actions → Variables**, you can set either of these repository variables. Run **Publish TokenPhage badge** again to apply the change. [GitHub repository variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables#creating-configuration-variables-for-a-repository)

| Variable | When to use it |
| --- | --- |
| `TOKENPHAGE_USERNAME` | Set this to the GitHub username you synced with TokenPhage if it differs from the fork owner, for example when an organization hosts the badges. Changing the username also changes the SVG filenames. |
| `TOKENPHAGE_PET_URL` | Choose a different character for both badges by entering its Codex Pets page URL, such as `https://codex-pets.net/#/pets/umaru`. |

## Preview locally

Replace `YOUR_USERNAME` with the GitHub username you synced to TokenPhage.

```bash
python3 -m pip install -r requirements.txt
python3 build_pages.py YOUR_USERNAME
python3 -m http.server 8000 --directory _site
```

Open the local site to see both badges. To build with another character, pass its page URL with `--pet`. [Local preview](http://localhost:8000)

To try different usernames, characters, and themes interactively, run `python3 server.py`. You can also request a badge at `/badge/YOUR_USERNAME?theme=grass-claude`. When passing a character URL in the `pet` query parameter, encode the `#` as `%23`. [Local badge picker](http://localhost:8787)
