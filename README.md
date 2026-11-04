# nk-nerd-font

OFL 1.1 한글 글꼴 모음입니다. 터미널 갈래 **NK Mono**·**NK Pixel**은 한글·영문·Nerd Fonts 아이콘이
셀 그리드에 정확히 맞는 고정폭이고, 문서·읽기 갈래 **NK Sans**·**NK Serif**·**NK Novel**·**NK Comics**는
비례폭입니다. NK Pixel은 마인크래프트·테라리아 같은 픽셀아트 게임용 포맷으로도 배포할 예정입니다.
가족별 설계는 [docs/FAMILIES.md](docs/FAMILIES.md)에 있습니다.

- 기획안: [docs/PLAN.md](docs/PLAN.md)
- 로드맵: [docs/ROADMAP.md](docs/ROADMAP.md)

## 현재 상태 (프로토타입 v0.1.0)
여섯 가족 모두 빌드되고 검사를 통과합니다. 터미널 갈래는 Nerd Font / Nerd Font Mono 패치와 터미널 호환 검사,
문서·읽기 갈래는 줄 높이(황금비)·한글 11,172자 검사를 거칩니다. 정식 릴리스 전입니다.

| 가족 | 갈래 | 영문 | 한글 | 굵기 |
| --- | --- | --- | --- | --- |
| NK Mono | 터미널 | JetBrains Mono | D2Coding 한글 | Regular, Bold |
| NK Pixel | 터미널·게임 | Neo둥근모 Code (16px 격자) | 〃 | Regular |
| NK Sans | 문서 | IBM Plex Sans | 본고딕 KR (Source Han Sans KR) | Regular, Bold |
| NK Serif | 문서 | IBM Plex Serif | 본명조 KR (Source Han Serif KR), 한 단계 굵게 | Regular, Bold |
| NK Novel | 읽기 | Crimson Text | 고운바탕 | Regular, Bold |
| NK Comics | 만화·손글씨 | 개구 Gaegu (펜 필기) | 같은 소스 + 나눔손글씨 펜 보충 | Light, Regular, Bold |

- 소개 페이지(GitHub Pages): https://naturalkei.github.io/nk-font-r1/ — `release` 브랜치에 push될 때만 `.github/workflows/pages.yml`이 다시 빌드(Nerd Fonts 패치 포함)해 배포합니다.
  `main` 병합으로는 배포되지 않으니, 공개할 때 `make release-pages`(= `git push origin main:release`)로 `release`를 `main`까지 올립니다.
- 조절 도구 **NK Studio**: `nkfont studio` → 브라우저에서 한글 크기·세로 위치를 슬라이더로 바꾸며 저장값과 나란히 비교하고,
  "중심 맞춤"·"높이 비율" 규칙 버튼으로 값을 제안받은 뒤 `config/families/*.toml`에 저장합니다.
- **프리셋 비교**(`/presets`): 가족·굵기·한글 축·OpenType 기능 조합을 `config/presets/*.toml`에 저장해 두고
  같은 샘플(한글/영문/코드/터미널/직접 입력)로 여러 개를 나란히, JetBrains Mono·D2Coding 같은 기준 글꼴과 함께 봅니다.
- **스페시먼**(`/specimen`): 가족별 큰 샘플, NK 축(굵기·GRAD·크기·폭·세로 위치·기울기·자간·φ 줄 간격) 패널,
  φ 비율 스타일(제목 1~3·본문·캡션) 블록을 직접 고쳐 쓰는 워크벤치. 프리셋으로 저장·비교로 바로 이어집니다.
- **데스크톱 앱**: `make app` (= `pip install -e ".[app]"` + `nkfont app`) → 위 화면을 네이티브 창(macOS WebKit)으로.
  `make app-install`은 `~/Applications/NK Studio.app` 런처를 만들어 Launchpad·Dock에서 열 수 있게 합니다.
  업데이트는 메뉴 **업데이트 → 업데이트 확인…**(`/update`): `git pull --ff-only` 후 다시 시작. 커밋하지 않은 변경이나
  로컬 커밋이 있으면 멈추고, `pyproject.toml`이 바뀌었을 때만 의존성을 다시 설치합니다.

## 개발
```bash
make setup          # Python 3.11+ 가상환경과 nkfont CLI
make build          # 업스트림 폰트 내려받기(SHA256 고정) + 마스터 빌드
make patch          # Docker로 Nerd Fonts 패치 (nerdfonts/patcher)
make check proof    # 터미널 호환 검사 + 교정 시트
make tune           # 한글 스케일 비교 시트
make test lint
nkfont build all     # 여섯 가족 모두 (mono|pixel|sans|serif|novel|comics)
nkfont studio       # 한글 미세 조절 웹 UI (http://127.0.0.1:8765) · /presets · /specimen · /lab (기준 글자 + 핵심 변수) · /lab/advanced
nkfont app          # 같은 화면을 데스크톱 창으로 (pywebview, --page specimen|studio|lab|site|update)
nkfont site         # 소개 페이지 조립: build/site (WOFF2, 다운로드 zip, fonts.json)
make qa             # 테스트 자동화: 린트·테스트·빌드·검사·재현성·골든 이미지 (docs/TESTING.md)
```
VS Code/Codespaces는 `.devcontainer/`를 쓰면 FontForge, ttfautohint, Docker까지 준비됩니다.

## 라이선스
폰트: SIL Open Font License 1.1 ([OFL.txt](OFL.txt)). 업스트림 Reserved Font Name(`Source` 등)은
이름에 쓰지 않습니다. Nerd Fonts 아이콘은 세트별 라이선스를 따릅니다. 빌드 도구 코드(`src/`, `tests/`)는 MIT
([LICENSE](LICENSE))입니다.
