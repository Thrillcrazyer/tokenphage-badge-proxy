# TokenPhage 배지 후처리

공식 Claude SVG에서 통계와 애니메이션을 가져와 회색 팔레트와 macOS 스타일 상단 바를 적용합니다. Codex Pets 캐릭터의 아홉 가지 표정과 동작을 무작위 순서로 반복하고 누적 토큰은 파란색으로 표시합니다.

## GitHub Pages 배지

`Thrillcrazyer/tokenphage-badge-proxy`의 첫 배포가 끝나면 다음 한 줄을 프로필 README에 붙이세요.

```markdown
![Thrillcrazyer의 TokenPhage 배지](https://thrillcrazyer.github.io/tokenphage-badge-proxy/badges/Thrillcrazyer.svg)
```

처음 배포할 때는 이 프로젝트를 위 이름의 GitHub 저장소 `main` 브랜치에 올리고, 저장소의 **Settings → Pages → Build and deployment → Source**에서 **GitHub Actions**를 선택하세요. **Actions → Publish TokenPhage badge → Run workflow**로 첫 배포를 실행할 수 있습니다.

이후 `main`에 푸시하거나 6시간 주기의 예약 작업이 실행되면 통계와 캐릭터를 다시 받아 같은 주소에 게시합니다. TokenPhage에 해당 계정의 동기화 기록이 필요합니다. 생성에 실패하면 마지막으로 배포한 배지를 계속 제공합니다.

로컬에서도 동일한 정적 사이트를 만들 수 있습니다.

```bash
python3 -m pip install -r requirements.txt
python3 build_pages.py Thrillcrazyer
python3 -m http.server 8000 --directory _site
```

캐릭터는 기본값인 Umaru를 사용합니다. 변경하려면 워크플로의 생성 명령에 `--pet 'https://codex-pets.net/#/pets/캐릭터ID'`를 추가하세요.

## 로컬 프록시

```bash
python3 -m pip install -r requirements.txt
python3 server.py
```

브라우저에서 `http://localhost:8787/badge/YOUR_GITHUB_USERNAME?theme=claude`를 열면 배지를 확인할 수 있습니다. 해당 사용자명으로 TokenPhage에서 동기화한 기록이 있어야 합니다.

서버에 공개 HTTPS 주소를 연결한 뒤 GitHub README에 이미지로 붙일 수 있습니다.

```markdown
[![TokenPhage](https://badge.example.com/badge/YOUR_GITHUB_USERNAME?theme=claude)](https://github.com/TOKENPHAGE)
```

기본 캐릭터는 [Umaru (yc)](https://codex-pets.net/#/pets/umaru)입니다. 다른 캐릭터를 쓰려면 Codex Pets 페이지 주소를 `pet`에 넣으세요. 주소의 `#`는 브라우저에서 서버로 전달되도록 `%23`으로 적습니다.

```text
http://localhost:8787/badge/YOUR_GITHUB_USERNAME?pet=https://codex-pets.net/%23/pets/umaru
```
