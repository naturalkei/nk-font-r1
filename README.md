# nk-nerd-font

터미널에서 한글·영문·Nerd Fonts 아이콘이 셀 그리드에 정확히 맞는 OFL 1.1 한글 고정폭 폰트입니다.
**NK Sans**, **NK Serif**, **NK Pixel** 세 가족으로 개발하며, NK Pixel은 마인크래프트·테라리아 같은
픽셀아트 게임에서도 쓸 수 있는 포맷으로 함께 배포할 예정입니다.

- 기획안: [docs/PLAN.md](docs/PLAN.md)
- 로드맵: [docs/ROADMAP.md](docs/ROADMAP.md)

## 현재 상태
NK Sans Regular/Bold (JetBrains Mono + 본고딕 KR) 빌드 파이프라인과 Nerd Font / Nerd Font Mono 패치가
동작합니다. 정식 릴리스 전입니다.

## 개발
```bash
make setup          # Python 3.11+ 가상환경과 nkfont CLI
make build          # 업스트림 폰트 내려받기(SHA256 고정) + 마스터 빌드
make patch          # Docker로 Nerd Fonts 패치 (nerdfonts/patcher)
make check proof    # 터미널 호환 검사 + 교정 시트
make tune           # 한글 스케일 비교 시트
make test lint
make qa             # 테스트 자동화: 린트·테스트·빌드·검사·재현성·골든 이미지 (docs/TESTING.md)
```
VS Code/Codespaces는 `.devcontainer/`를 쓰면 FontForge, ttfautohint, Docker까지 준비됩니다.

## 라이선스
폰트: SIL Open Font License 1.1 ([OFL.txt](OFL.txt)). 업스트림 Reserved Font Name(`Source` 등)은
이름에 쓰지 않습니다. Nerd Fonts 아이콘은 세트별 라이선스를 따릅니다. 빌드 도구 코드(`src/`, `tests/`)는 MIT
([LICENSE](LICENSE))입니다.
