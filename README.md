# nk-nerd-font

터미널에서 한글·영문·Nerd Fonts 아이콘이 셀 그리드에 정확히 맞는 OFL 1.1 한글 고정폭 폰트입니다.
**NK Sans**, **NK Serif**, **NK Pixel** 세 가족으로 개발하며, NK Pixel은 마인크래프트·테라리아 같은
픽셀아트 게임에서도 쓸 수 있는 포맷으로 함께 배포할 예정입니다.

- 기획안: [docs/PLAN.md](docs/PLAN.md)
- 로드맵: [docs/ROADMAP.md](docs/ROADMAP.md)

## 현재 상태 (프로토타입 v0.1.0)
세 가족 모두 빌드되고 Nerd Font / Nerd Font Mono 패치와 터미널 호환 검사를 통과합니다. 정식 릴리스 전입니다.

| 가족 | 영문 | 한글 | 굵기 |
| --- | --- | --- | --- |
| NK Sans | JetBrains Mono | 본고딕 KR (Source Han Sans KR) | Regular, Bold |
| NK Serif | IBM Plex Mono | 본명조 KR (Source Han Serif KR), 한 단계 굵게 | Regular, Bold |
| NK Pixel | Neo둥근모 Code (16px 격자) | 〃 | Regular |

- 소개 페이지(GitHub Pages): https://naturalkei.github.io/nk-font-r1/ — `main`에 병합되면 `.github/workflows/pages.yml`이 다시 빌드해 배포
- 조절 도구 **NK Studio**: `nkfont studio` → 브라우저에서 한글 크기·세로 위치를 슬라이더로 바꾸며 저장값과 나란히 비교하고,
  "중심 맞춤"·"높이 비율" 규칙 버튼으로 값을 제안받은 뒤 `config/families/*.toml`에 저장합니다.

## 개발
```bash
make setup          # Python 3.11+ 가상환경과 nkfont CLI
make build          # 업스트림 폰트 내려받기(SHA256 고정) + 마스터 빌드
make patch          # Docker로 Nerd Fonts 패치 (nerdfonts/patcher)
make check proof    # 터미널 호환 검사 + 교정 시트
make tune           # 한글 스케일 비교 시트
make test lint
nkfont build serif && nkfont build pixel   # 다른 두 가족
nkfont studio       # 한글 미세 조절 웹 UI (http://127.0.0.1:8765)
nkfont site         # 소개 페이지 조립: build/site (WOFF2, 다운로드 zip, fonts.json)
make qa             # 테스트 자동화: 린트·테스트·빌드·검사·재현성·골든 이미지 (docs/TESTING.md)
```
VS Code/Codespaces는 `.devcontainer/`를 쓰면 FontForge, ttfautohint, Docker까지 준비됩니다.

## 라이선스
폰트: SIL Open Font License 1.1 ([OFL.txt](OFL.txt)). 업스트림 Reserved Font Name(`Source` 등)은
이름에 쓰지 않습니다. Nerd Fonts 아이콘은 세트별 라이선스를 따릅니다. 빌드 도구 코드(`src/`, `tests/`)는 MIT
([LICENSE](LICENSE))입니다.
