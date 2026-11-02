# nk-font 개발 로드맵

> 2026-11-02 작성 · 기준 문서: [PLAN.md](PLAN.md)
> 목표 수준: MonoLisa(monolisa.dev)처럼 **포트폴리오로 내세울 수 있는 완성도**의 폰트와 소개 사이트

MonoLisa는 구성과 완성도의 기준으로만 참고합니다. 사이트 디자인, 문구, 브랜딩은 nk-font 고유의 것으로 만들고 MonoLisa의 디자인이나 자산을 가져오지 않습니다.

---

## 1. "포트폴리오급"의 정의

MonoLisa 같은 상용 코딩 폰트가 신뢰를 주는 이유는 세 가지입니다. 폰트 자체의 설계 근거가 분명하고, 사이트에서 직접 만져 보며 확인할 수 있고, 설치와 사용이 막힘없습니다. nk-font는 여기에 "한글 터미널 정렬"이라는 분명한 차별점을 더합니다. 아래 기준을 1.0의 완료 조건으로 삼습니다.

| 영역 | 1.0 완료 기준 |
| --- | --- |
| **정렬** | 자동 폭 검사 0건, 호환성 매트릭스 10개 환경(§5) 전부 통과, 스크린샷으로 증명 |
| **한글 품질** | 영문 대비 높이·굵기·중심이 맞도록 조절값 확정, 12~16px에서 획 뭉개짐 없음, 받침 유무에 따른 시각 정렬 규칙 적용 |
| **패밀리 완성도** | NK Sans 8 weight × (정체 + 이탤릭) = 16종, 각각 Nerd Font / Nerd Font Mono |
| **기능** | 영문 합자(`calt`) 끄고 켜기, 스타일 세트(`ss01~`, `cv01~`) 문서화, `0` 점/사선 변형 |
| **렌더링** | macOS, Windows(ClearType 12~14px), Linux(FreeType) 세 환경 교정 시트 공개 |
| **배포** | GitHub Releases, Homebrew tap, Scoop bucket, 웹폰트 CDN(jsDelivr) |
| **문서** | 소개 사이트, 터미널별 설치·설정 가이드, 변경 이력, 라이선스 고지 |

---

## 2. 마일스톤

기간은 혼자 진행하는 사이드 프로젝트 기준의 대략적인 추정입니다.

### M0 기반 구축 (완료, 2026-11)
* 기획안, 빌드 도구 `nkfont`(fetch / build / patch / check / proof / tune), CI, 개발 컨테이너, Claude 스킬
* 테스트 자동화 CLI `nkfont qa`(프로필 quick / ci / release), 재현 빌드, 골든 이미지 회귀 검사, `nkfont diff` ([TESTING.md](TESTING.md))
* NK Sans Regular·Bold 빌드와 Nerd Font·Nerd Font Mono 패치가 QA 전 항목 통과

### M1 NK Sans 알파 (약 3주)
* `nkfont tune`으로 한글 스케일·dy 확정, 결정 근거를 교정 시트와 함께 기록
* 8 weight 확장과 weight 매핑표 확정 (JetBrains Mono 8단계 ↔ 본고딕 7단계)
* 이탤릭: 정체 한글 사용 vs 한글 기울임(약 9°, 이탤릭 각도에 맞춤) 비교 후 결정
* 힌팅 실험: 영문 원본 힌팅 유지 + 한글 무힌팅 vs 전체 ttfautohint를 Windows에서 비교
* 첫 GitHub Pre-release (`v0.1.0-alpha`), 지인·커뮤니티 피드백 수집
* **완료 기준:** 호환성 매트릭스 중 macOS(iTerm2, Terminal.app), Linux(GNOME Terminal, kitty, WezTerm) 통과

### M2 NK Sans 1.0 + 소개 사이트 (약 6주)
* 조절 도구 T2(로컬 웹 UI) 완성 후 받침 유무별 dy 같은 규칙 기반 미세 조절
* 렌더링 교정: Windows ClearType 12~14px, Linux FreeType 가벼운 힌팅
* 소개 사이트 1차 공개 (§3)
* Homebrew tap, Scoop bucket, jsDelivr 웹폰트
* **완료 기준:** §1 표 전체 충족, `v1.0.0` 릴리스

### M3 NK Pixel (약 6주)
* 16×16 픽셀 마스터 (Neo둥근모 Code 기반으로 확정, OFL 1.1, RFN 때문에 이름은 NK Pixel 유지)
* 출력: TTF, BDF/PCF, 마인크래프트 리소스팩(unihex), BMFont, 테라리아 XNB
* 예제 팩과 게임 내 스크린샷, 사이트에 Pixel 전용 섹션
* Starship·Powerline에 자주 쓰는 아이콘 50~100개 픽셀 리드로잉
* **완료 기준:** 마인크래프트 Java 최신판, 테라리아(tModLoader)에서 한글 표시 확인

### M4 NK Serif (약 4주)
* IBM Plex Mono + 본명조 KR, 작은 크기를 위한 weight 한 단계 올림 매핑
* 사이트에 세 가족 비교 화면
* **완료 기준:** NK Sans와 같은 QA 기준 통과

### M5 확장 (이후)
* 조합형 자모(macOS NFD 파일명) 폰트 차원 지원
* 한자 KS X 1001 4,888자
* 조절 도구 T3(Tauri 데스크톱 앱)
* 가변 폰트(weight 축) 검토

---

## 3. 소개 사이트 계획 (nk-font 사이트)

정적 사이트(Astro 또는 Vite + 순수 TS)로 만들고 GitHub Pages에 배포합니다. 폰트 빌드 산출물(WOFF2)을 CI에서 그대로 가져다 쓰므로 사이트가 항상 최신 빌드를 보여 줍니다.

### 3.1 페이지 구성
| 섹션 | 내용 | 핵심 장치 |
| --- | --- | --- |
| **히어로** | 한 줄 소개와 터미널 화면 | 실제 Starship 프롬프트와 한글 경로가 섞인 터미널을 HTML로 재현하고, 셀 격자 오버레이를 켜고 끌 수 있음 |
| **직접 입력해 보기** | 사용자가 문장을 입력 | 가족(Sans/Serif/Pixel)·weight·크기·합자·스타일 세트 토글, 배경 테마 전환 |
| **왜 nk-font인가** | 설계 근거 | 1:2 그리드, wcwidth 일치, 줄 높이와 Powerline 이음새, 한글 높이 조절의 전후 비교 이미지 |
| **코드 샘플** | 여러 언어 | Python, Rust, TypeScript, Go, 셸 스크립트에 한글 주석·문자열 포함, 에디터 테마 3~4종 |
| **터미널 쇼케이스** | 실제 캡처 | iTerm2, WezTerm, kitty, GNOME Terminal, Windows Terminal 스크린샷 갤러리 |
| **글리프 탐색기** | 전체 글자 | 유니코드 블록별 그리드, 글자 클릭 시 코드포인트·폭(1칸/2칸)·Nerd 아이콘 이름 표시, 검색 |
| **Pixel 섹션** | 게임 | 마인크래프트·테라리아 화면, 정수 배율 미리보기, 리소스팩 내려받기 |
| **비교** | 다른 폰트와 | D2Coding, Sarasa Mono K 등과 같은 문장을 나란히 (공정하게, 각 폰트의 라이선스 범위 안에서) |
| **설치** | OS·터미널별 | Homebrew/Scoop 명령, iTerm2·WezTerm·Alacritty·VS Code 설정 스니펫 복사 버튼 |
| **변경 이력·라이선스** | | 릴리스 노트, OFL 전문, 업스트림·아이콘 고지 |

### 3.2 품질 기준
* 모바일 360px부터 깨짐 없음, 다크·라이트 모드
* Lighthouse 성능·접근성 90점 이상, 폰트는 글자 범위별 분할(unicode-range)로 필요한 부분만 로드
* 모든 이미지와 데모는 실제 빌드 결과로 생성 (가짜 렌더 금지), CI가 스크린샷을 갱신

---

## 4. 작업 흐름 (트랙별)

| 트랙 | M1 | M2 | M3 | M4 |
| --- | --- | --- | --- | --- |
| 타입 디자인 | 스케일·weight 확정 | 규칙 기반 미세 조절, 이탤릭 | 픽셀 마스터, 아이콘 리드로잉 | 명조 weight 보정 |
| 테스트 자동화 | 골든 이미지 weight 전체로 확대, 렌더링 환경 고정 | 실제 터미널 스크린샷 자동화(Xvfb + kitty/Alacritty/WezTerm) | 게임 포맷 검증기(unihex, BMFont 파서) | Serif 골든 추가 |
| 엔지니어링 | 8 weight, 힌팅 실험 | 렌더링 교정, 웹폰트 분할 | 비트맵·게임 포맷 출력기 | Serif 파이프라인 |
| 조절 도구 | T1 개선 | T2 웹 UI | 픽셀 격자 편집 보조 | |
| 사이트 | 와이어프레임 | 1차 공개 | Pixel 섹션 | 가족 비교 |
| 배포·커뮤니티 | 알파 릴리스 | 패키지 매니저, 1.0 공지 | 게임 커뮤니티 공유 | |

---

## 5. 호환성 매트릭스 (릴리스마다)

Starship(Nerd Font Symbols 프리셋), zsh + Powerlevel10k, iTerm2, macOS Terminal.app, GNOME Terminal, Konsole, kitty, Alacritty, WezTerm, Windows Terminal, VS Code, JetBrains IDE. 각 환경에서 같은 테스트 화면(한글 경로 프롬프트, `ls -l` 한글 파일명, 박스 드로잉 표, 합자, 아이콘 줄)을 캡처해 `docs/compat/<버전>/`에 남깁니다.

---

## 6. 위험과 대응

| 위험 | 대응 |
| --- | --- |
| 본고딕 한글을 그대로 쓰면 1200 셀 안에서 작고 성기게 보임 | M1에서 스케일 범위를 교정 시트로 확정, M2에서 규칙 기반 보정. 그래도 부족하면 M5에 고정폭 최적화 한글(자소 폭 재설계) 검토 |
| ttfautohint가 한글을 잘 처리하지 못할 수 있음 | 한글 무힌팅 + 영문 원본 힌팅 유지안을 기본 대안으로 둠 |
| Nerd Fonts 아이콘 라이선스 혼재 | 세트별 고지(`LICENSES/`, `NOTICE`), "100% OFL" 표기 금지 |
| 픽셀 베이스 RFN | Neo둥근모 RFN(`Neo둥근모`, `NeoDunggeunmo Code`)을 이름 검사 목록에 추가해 CI가 막음 |
| 게임 쪽 폰트 교체 방식이 버전마다 바뀜 | 지원 버전을 명시하고 예제 팩에 버전 표기 |
| 혼자 진행하는 일정 | 마일스톤마다 릴리스 가능한 결과물을 두어 중간에 멈춰도 쓸 수 있게 함 |
