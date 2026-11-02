# [기획서] nk-nerd-font: 터미널 완벽 호환 한글 Nerd Font (Sans · Serif · Pixel)

> 문서 상태: v0.2 초안 (2026-11-02) · 원본: `nerd_font.md`(가칭 K-Mono Nerd Font) 개정판
> 레포: `naturalkei/nk-font-r1` · 라이선스: SIL OFL 1.1 (아이콘 세트는 별도 고지, §7 참고)

---

## 0. 초안 대비 주요 변경 사항

실제 업스트림 폰트 파일을 내려받아 메트릭을 측정하고, Nerd Fonts 패처 v3.5.1 소스를 직접 확인한 결과를 반영했습니다.

| # | 초안 내용 | 문제 | 개정 |
| --- | --- | --- | --- |
| 1 | 터미널 Mono 버전을 `--mono`로 패치 | 패처의 `--mono`는 **기존 글리프까지 전부 1칸 폭(600)으로 강제**합니다(`set_sourcefont_glyph_widths`). 한글 1200 폭이 600으로 바뀌어 1:2 그리드가 깨집니다. | `--single-width-glyphs` 사용 (아이콘만 1칸, 한글 폭 유지, 이름은 동일하게 "Nerd Font Mono") |
| 2 | Propo 버전 = `--complete --careful` | 옵션 없이 패치하면 Propo가 아니라 기본 "Nerd Font" 변형입니다. Propo는 `--variable-width-glyphs`이며 비례폭이라 터미널·코드 에디터용이 아닙니다. | 배포 변형을 "Nerd Font"(기본)와 "Nerd Font Mono" 두 가지로 정리, Propo는 제외 |
| 3 | 줄 높이 `880 / -120` 고정 | 이 값은 본고딕의 **CJK 표의문자 em-box**(OS/2 Typo 값)입니다. JetBrains Mono의 실제 줄 메트릭은 `1020 / -300`이고 글리프 bbox는 `yMax 1165 / yMin -400`입니다. 880/-120을 쓰면 영문 박스 드로잉이 셀을 넘쳐 끊기고, `usWin*`이 bbox보다 작아 Windows에서 글자 위아래가 잘립니다. | 영문 베이스의 줄 메트릭을 유지하고, `usWin*`은 최종 bbox 기준으로 계산 |
| 4 | UPM `1000`(또는 `2048`)으로 통일 | 기준이 모호합니다. 반각 폭 600은 UPM 1000일 때만 맞는 값입니다. | **영문 베이스 UPM에 맞춤.** JetBrains Mono = 1000 → 반각 600 / 전각 1200. Pretendard(2048)를 쓰면 ×0.488 스케일 필요 |
| 5 | 한글 93% 축소 = "숨구멍 확보" | 본고딕 KR 한글은 원래 advance 920, 실제 외곽 bbox 약 830×910입니다. 1200 셀에서는 오히려 여백이 넘치므로, 스케일은 **가로 여백이 아니라 영문 대문자 높이 대비 한글 높이**로 정해야 합니다. | 균등 스케일 `s`와 Y 오프셋 `dy`를 설정값으로 두고 교정 시트로 결정 (시작값 s≈0.92~1.0) |
| 6 | `U+1100~U+11FF` 조합형 자모를 일반 글리프처럼 추출 | 중성·종성(U+1160~11FF)은 터미널(wcwidth)에서 폭 0으로 처리되고, 조합에는 `ljmo/vjmo/tjmo` GSUB가 필요합니다. 1200 폭으로 넣으면 폭 계산과 렌더링이 어긋납니다. | 1단계에서 제외. macOS NFD 파일명은 터미널의 NFC 정규화 옵션으로 해결, 조합형 지원은 2단계 |
| 7 | 모든 영역에 Panose·isFixedPitch만 설정 | `xAvgCharWidth`를 설정하지 않으면 한글 1만여 자 때문에 평균이 1100 안팎으로 계산되어 Windows 일부 앱에서 셀 폭이 2배로 잡힙니다. Panose `bProportion=9`는 `bFamilyType=2`일 때만 "고정폭" 의미입니다. | `xAvgCharWidth=600`, `bFamilyType=2` 추가. 패처가 값을 바꾸므로 **패치 이후** 다시 적용 |
| 8 | RFN 예시에 `JetBrains` 포함 | JetBrains Mono와 Geist Mono는 RFN이 **없습니다.** RFN이 있는 것은 본고딕/본명조(`Source`), Pretendard(`Pretendard`, `Source`), IBM Plex(`Plex`)입니다. | §7 표로 정리. 그래도 혼동 방지를 위해 독자 이름을 씁니다 |
| 9 | FontForge로 한/영 병합 | FontForge로 열고 다시 저장하면 복잡한 GSUB(문맥 치환 `calt`)가 손상될 수 있습니다. 본고딕은 CFF(3차 곡선)라 `ttfautohint`를 직접 쓸 수 없습니다. | 병합은 `fontTools`로 영문 TTF에 글리프만 주입, CFF→TrueType은 `cu2qu`로 변환 |
| 10 | 스타일 1종 | 사용자 방향: 터미널 완벽 호환 + **Sans · Serif · Pixel** 3종, Pixel은 마인크래프트·테라리아 등 픽셀아트 게임 호환까지 | §2, §5에 반영 |

---

## 1. 프로젝트 개요

### 1.1 목표
Starship, zsh(Oh My Zsh / Powerlevel10k), iTerm2, Linux 터미널(GNOME Terminal, Konsole, kitty, Alacritty, WezTerm, foot) 등에서 **한글·영문·Nerd Fonts 아이콘이 셀 그리드에서 어긋나지 않는** OFL 1.1 한글 고정폭 폰트를 Sans · Serif · Pixel 세 가족으로 개발하고 배포합니다. Pixel 가족은 터미널뿐 아니라 마인크래프트, 테라리아 같은 픽셀아트 게임과 게임 엔진에서도 쓸 수 있는 비트맵 포맷으로 함께 출력합니다.

### 1.2 해결할 문제
1. 기존 한글 코딩 폰트의 Nerd Fonts v3 심볼 누락 또는 구버전 코드포인트 (v3에서 Material Design Icons가 `U+F0001~`로 이동)
2. 터미널의 문자 폭 계산(wcwidth)과 폰트 advance 폭 불일치로 생기는 밀림·겹침
3. 줄 높이와 Powerline/박스 드로잉 글리프 높이 불일치로 생기는 프롬프트 끊김
4. 작은 크기(10~14pt)에서의 한글 가독성
5. 픽셀아트 환경에서 쓸 수 있는 OFL 한글 픽셀 폰트의 포맷 부족

### 1.3 범위 밖 (1차)
한자(KS X 1001 4,888자), 옛한글, 조합형 자모 조합, 가변 폰트(Variable)는 로드맵 후순위로 둡니다(§9).

---

## 2. 폰트 가족 구성과 베이스 폰트

### 2.1 명명 (결정 필요)
업스트림 RFN(`Source`, `Pretendard`, `Plex`)을 피하고, Nerd Fonts 패처가 이름 뒤에 `Nerd Font` / `Nerd Font Mono`를 자동으로 붙인다는 점을 고려해 **베이스 패밀리명에는 "Nerd"를 넣지 않습니다.**

| 가족 | 베이스 패밀리명(안) | 패치 결과 |
| --- | --- | --- |
| Sans | `NK Mono` | `NK Mono Nerd Font`, `NK Mono Nerd Font Mono` |
| Serif | `NK Mono Serif` | `NK Mono Serif Nerd Font`, `… Nerd Font Mono` |
| Pixel | `NK Pixel` | `NK Pixel Nerd Font`, `… Nerd Font Mono` + 게임용 비트맵 포맷 |

레포·패키지명은 `nk-nerd-font`로 통일합니다 (예: `font-nk-mono-nerd-font`).

### 2.2 베이스 폰트 후보 (실측 기준)

| 가족 | 영문 베이스 | 한글 베이스 | 비고 |
| --- | --- | --- | --- |
| **Sans** | **JetBrains Mono** (OFL, RFN 없음, UPM 1000, 폭 600, 글리프 1,754, `calt` 포함, 8 weight + italic) | **본고딕 KR** Source Han Sans KR (OFL, RFN `Source`, UPM 1000, CFF, 한글 advance 920, `ljmo/vjmo/tjmo` 포함, 7 weight) | 추천 조합. 대안 영문: Geist Mono (OFL, RFN 없음) |
| Sans 대안 | 〃 | Pretendard (OFL, RFN `Pretendard` + `Source`, UPM 2048, CFF, 한글 1770, **U+1100 자모 없음**) | Pretendard 한글은 본고딕 파생이라 이점이 작고 UPM 변환이 추가됨 → 비추천 |
| **Serif** | IBM Plex Mono (OFL, RFN `Plex`, 슬랩 세리프, 7 weight + italic) | 본명조 KR Source Han Serif KR (OFL, RFN `Source`) | 명조 가로획이 얇아 10~12pt에서 사라질 수 있음 → weight를 한 단계 올려 매핑(예: 영문 Regular ↔ 한글 Medium) 검토. Plex Mono UPM·폭은 착수 시 실측 필요 |
| **Pixel** | (단일 소스 권장, §2.3) | NeoDunggeunmo Code (Neo둥근모 코드, 16px 격자) 또는 Galmuri Mono (갈무리, OFL 확인됨, 11/9/7px) | 픽셀 폰트는 한·영이 **같은 픽셀 격자**여야 하므로 서로 다른 폰트를 스케일 병합하지 않음. Neo둥근모 라이선스는 착수 시 원문 확인 필요 |

### 2.3 Pixel 가족 원칙
* **격자:** 반각 8×16px / 전각 16×16px을 기본으로 합니다. GNU Unifont와 같은 규격이라 마인크래프트 `unihex` 포맷, Linux BDF/PCF와 그대로 호환됩니다. 작은 크기용으로 11px(갈무리 계열) 변형을 추가로 검토합니다.
* **외곽선 TTF:** 1px = 정수 unit (예: UPM 1024, 1px = 64 unit)으로 정사각형 외곽선을 생성하고 힌팅·스케일 보정은 하지 않습니다. 정수배 크기(16, 32, 48px)에서만 선명하므로 문서에 권장 크기를 명시합니다.
* **Nerd 아이콘:** 패처 아이콘은 벡터라 픽셀 느낌이 아닙니다. 1차는 그대로 쓰고, Starship/Powerline에 자주 쓰는 아이콘(약 50~100개)만 픽셀로 다시 그리는 것을 2차 과제로 둡니다.

---

## 3. 터미널 호환 기술 명세 (Sans · Serif 공통)

### 3.1 1:2 폭 규칙
터미널은 폰트 advance가 아니라 **wcwidth(유니코드 East Asian Width)** 로 셀 수를 정하므로, 폰트의 advance를 wcwidth 결과에 정확히 맞추는 것이 핵심입니다.

| 문자 분류 | wcwidth | advance (UPM 1000) |
| --- | --- | --- |
| 영문·숫자·기호, Nerd 아이콘(PUA, EAW=Ambiguous), 박스 드로잉 | 1 | **600** |
| 한글 음절 U+AC00~D7A3, 호환 자모 U+3131~318E, CJK 기호 U+3000~303F, 전각 U+FF01~FF60 | 2 | **1200** |
| 반각 한글 U+FFA0~FFDC | 1 | **600** |
| 결합 문자(Mn/Me), ZWJ 등 | 0 | **0** |

* **Ambiguous 문자는 한글 폰트에서 가져오지 않습니다.** 본고딕은 `·`(561), `─`(1000), `①`(1000) 등을 전각·비례폭으로 갖고 있어, 그대로 들여오면 터미널 폭과 어긋납니다. 영문 베이스에 있는 글리프는 절대 덮어쓰지 않고, EAW가 W/F인 코드포인트만 주입합니다.
* 허용 advance는 `{0, 600, 1200}` 세 값뿐이며 CI에서 전수 검사합니다(§6).

### 3.2 한글 배치 (스케일·정렬)
* **균등 스케일만 사용**합니다. 가로만 늘리면 세로획이 굵어져 영문과 획 굵기가 달라집니다.
* 기준: 본고딕 한글 외곽 높이 약 910 unit(y −77~834), JetBrains Mono 대문자 높이 730. 한글 높이를 대문자의 1.15~1.25배로 두는 것이 일반적이라 **s ≈ 0.92~1.0**에서 시작합니다.
* 트레이드오프: s=0.92이면 한글 폭이 약 770이라 1200 셀 안 좌우 여백이 각 215 정도로 넓어 보이고, s=1.05 이상이면 한글이 영문보다 지나치게 커집니다. 반각 600은 JetBrains Mono가 넓은 편이라 생기는 문제이므로, **교정 시트(proof)를 렌더링해 s와 dy를 결정**하고 `config/`에 기록합니다.
* 가로는 1200 셀 중앙 정렬, 세로는 한글 시각 중심(약 y 378)을 영문 대문자 중심(365)에 맞추는 `dy`를 적용합니다.
* weight 매핑표를 둡니다. JetBrains Mono(Thin~ExtraBold 8단계) ↔ 본고딕(ExtraLight~Heavy 7단계). 스케일이 획 굵기도 바꾸므로 매핑은 스케일 적용 후 눈으로 확인합니다. Italic에는 정체 한글을 넣습니다.

### 3.3 세로 메트릭 (줄 높이)
* **영문 베이스의 값을 유지합니다.** JetBrains Mono: `hhea 1020/-300`, `Typo 1020/-300`, `lineGap 0`, `USE_TYPO_METRICS` 켜짐. 박스 드로잉·블록 요소가 이 셀 높이에 맞춰 그려져 있어, 값을 바꾸면 위아래가 끊기거나 겹칩니다.
* `hhea`, `Typo`를 같은 값으로 두고 `lineGap=0`, `fsSelection` bit 7(USE_TYPO_METRICS)을 켭니다.
* `usWinAscent/usWinDescent`는 **최종 폰트의 실제 bbox 이상**이어야 Windows에서 잘리지 않습니다. 줄 높이와 분리된 값입니다.
* Nerd Fonts 패처는 이 메트릭을 읽어 Powerline 구분자 높이를 셀에 맞추므로, 세로 메트릭은 **패치 전에** 확정합니다.

### 3.4 고정폭 플래그 (패치 후 최종 적용)

```python
# scripts/fix_flags.py — Nerd 패치 이후 마지막에 실행
from fontTools.ttLib import TTFont

HALF = 600              # 영문 베이스 반각 폭 (UPM 1000 기준)
ASC, DESC = 1020, -300  # 영문 베이스(JetBrains Mono) 줄 메트릭 유지

def enforce_terminal_flags(path: str) -> None:
    f = TTFont(path)
    os2, hhea, glyf = f["OS/2"], f["hhea"], f["glyf"]

    # 1) 고정폭 신호
    f["post"].isFixedPitch = 1
    os2.panose.bFamilyType = 2      # Latin Text: 이때만 bProportion=9가 "고정폭"
    os2.panose.bProportion = 9
    os2.xAvgCharWidth = HALF        # 한글 때문에 평균이 커져 셀 폭이 2배로 잡히는 문제 방지

    # 2) 줄 메트릭: hhea와 Typo 일치, lineGap 0, USE_TYPO_METRICS
    hhea.ascent, hhea.descent, hhea.lineGap = ASC, DESC, 0
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ASC, DESC, 0
    os2.fsSelection |= 1 << 7

    # 3) usWin*: 실제 글리프 bbox를 덮어야 Windows 클리핑이 없음
    y_max = max(getattr(glyf[g], "yMax", 0) for g in f.getGlyphOrder())
    y_min = min(getattr(glyf[g], "yMin", 0) for g in f.getGlyphOrder())
    os2.usWinAscent = max(ASC, y_max)
    os2.usWinDescent = max(-DESC, -y_min)

    f.save(path)
```

참고: fontconfig는 1:2 폰트를 `spacing=dual`(90)로 인식합니다. 대부분의 Linux 터미널은 문제없지만 `spacing=mono`만 나열하는 앱이 있는지 호환성 매트릭스(§6.3)에서 확인합니다.

### 3.5 코딩 합자와 OpenType 보존
* 영문 TTF를 그대로 두고 `fontTools`로 한글 글리프·`hmtx`·`cmap` 항목만 추가합니다. 영문 `GSUB/GPOS`(`calt`, `cv01~cv20`, `ss01~` 등)는 바이트 단위로 보존됩니다.
* 한글 쪽 `GSUB`는 1단계에서 가져오지 않습니다(조합형 자모 제외와 같은 이유).
* 글리프 수 예산: JetBrains Mono 1,754 + 한글 약 11,400 + Nerd Fonts complete 약 1만 → 약 2.3~2.5만으로 TrueType 한도 65,535 안쪽입니다.

### 3.6 조합형 자모와 macOS NFD
* macOS는 파일명을 NFD(첫가끝 자모 U+1100~)로 저장해서 `ls` 출력이 자모 단위로 풀려 보일 수 있습니다. 이것은 폰트보다 터미널 설정으로 푸는 것이 확실합니다. iTerm2의 Unicode normalization(NFC), WezTerm의 `normalize_output_to_unicode_nfc` 등을 README 가이드에 넣습니다.
* 폰트 차원의 조합 지원(초성 1200·중종성 0 폭 + `ljmo/vjmo/tjmo`)은 2단계 과제입니다.

### 3.7 힌팅
* `ttfautohint`는 TrueType(2차 곡선) 전용이라 본고딕 CFF는 `cu2qu` 변환이 먼저 필요합니다.
* ttfautohint의 한글 스크립트 지원과 결과 품질은 미검증입니다. 1차는 (a) 영문 원본 힌팅 유지 + 한글 무힌팅, (b) 전체 ttfautohint 두 가지를 Windows 10~14pt에서 비교해 결정합니다. macOS는 힌팅을 무시합니다.
* Pixel 가족은 힌팅하지 않습니다.

---

## 4. Nerd Fonts 패치

* 도구: `nerdfonts/patcher` Docker 이미지, **버전 태그 고정** (확인한 최신 패처: v3.5.1)
  `docker run --rm -v $PWD/build/master:/in -v $PWD/build/patched:/out nerdfonts/patcher:<tag> <옵션>`
* 배포 변형 2종:

| 변형 | 옵션 | 용도 |
| --- | --- | --- |
| `… Nerd Font` | `--complete --careful` | 아이콘이 다음 칸으로 살짝 넘치는(overhang) 큰 아이콘. WezTerm·kitty·iTerm2 등 대부분 터미널 |
| `… Nerd Font Mono` | `--complete --careful --single-width-glyphs` | 아이콘을 1칸 안에 강제. 아이콘 겹침이 생기는 터미널, IDE |

* **`--mono`(`-s`)는 쓰지 않습니다.** 패처 소스상 `--mono`는 모든 기존 글리프 폭을 반각으로 바꿔 한글 1200이 600이 됩니다. 이름 접미사("Mono")는 `--single-width-glyphs`로도 똑같이 붙습니다.
* 패처는 영문(`I M W a i m .`)만 보고 고정폭 여부를 판정하므로 한글 1200 폭이 있어도 경고 없이 동작합니다.
* `--careful`은 기존 글리프를 덮어쓰지 않으므로 영문 베이스의 박스 드로잉이 유지됩니다(`--boxdrawing`은 쓰지 않음).
* 패처가 Panose·xAvgCharWidth·이름 테이블을 건드리므로 패치 뒤에 §3.4 스크립트와 이름 검증을 다시 실행합니다.

---

## 5. Pixel 가족: 게임·픽셀아트 호환 출력

하나의 픽셀 마스터(16×16 격자, 비트맵 원본)에서 아래 포맷을 모두 생성합니다.

| 대상 | 포맷 | 비고 |
| --- | --- | --- |
| 터미널·OS | TTF/OTF (정사각형 외곽선) | Nerd 패치 적용 대상 |
| Linux X11·xterm·일부 터미널 | BDF, PCF | 비트맵 그대로 사용, 안티앨리어싱 없음 |
| **마인크래프트** (Java Edition 리소스팩) | `assets/minecraft/font/default.json` + `unihex` 프로바이더(.hex) 또는 `bitmap` 프로바이더(PNG 시트), 보조로 `ttf` 프로바이더 | 기본 폰트가 Unifont(8×16/16×16)라 같은 격자의 `unihex`가 가장 자연스럽게 교체됨. 팩 포맷 번호는 대상 게임 버전별로 확인 필요 |
| **테라리아** | XNA SpriteFont `.xnb` (tModLoader 리소스팩/모드로 교체) | TTF + 문자 범위로 MonoGame 콘텐츠 파이프라인에서 빌드. 한글 1.1만 자는 텍스처가 커지므로 KS X 1001 2,350자 서브셋 변형도 함께 제공 검토 |
| 범용 게임 엔진 (Unity, Godot, Phaser, GameMaker 등) | AngelCode BMFont `.fnt` + PNG 아틀라스 | 대부분 엔진이 직접 읽음 |
| 웹 | WOFF2 | `image-rendering`/`font-smooth` 안내 |

* 게임용 포맷은 정수 배율(1×, 2×, 3×) 버전을 함께 냅니다.
* 각 게임의 폰트 교체 방식(팩 포맷 번호, tModLoader 리소스팩 구조)은 버전에 따라 바뀌므로 착수 시 실제 게임에서 확인하고 예제 팩을 레포의 `examples/`에 둡니다.
* 게임 리소스팩에 넣어 재배포할 때도 OFL 고지(라이선스 파일 동봉)가 필요하다는 점을 README에 적습니다.

---

## 6. 품질 보증 (QA)

### 6.1 자동 검사 (CI에서 매 빌드)
1. **폭 전수 검사:** `cmap`의 모든 코드포인트에 대해 Python `wcwidth` 결과(0/1/2)와 advance(0/600/1200)가 일치하는지 확인
2. **메트릭 검사:** `usWin* ≥ bbox`, `hhea == Typo`, `lineGap == 0`, `isFixedPitch == 1`, `xAvgCharWidth == 600`, Panose `2 / … / 9`
3. **이름 검사:** RFN 단어(`Source`, `Pretendard`, `Plex`)가 name 테이블·파일명에 없는지
4. **OpenType 보존:** 영문 베이스와 결과물의 GSUB feature 목록 비교 (`calt` 등 누락 여부)
5. **Font Bakery** `universal` 프로파일
6. 동일 입력 → 동일 출력(재현 빌드): `head.created/modified` 고정, 업스트림 폰트와 패처 이미지 버전·SHA256 고정

### 6.2 시각 검사
* 교정 시트: 한·영 혼용 문장, `0O1lI`, 괄호·따옴표, 합자, 박스 드로잉 표, Powerline 구분자, Starship 프롬프트 샘플을 HarfBuzz(`hb-view`)로 렌더링해 PR마다 이미지로 첨부
* Pixel: 정수 배율에서 픽셀 정렬, 마인크래프트·테라리아 실제 화면 캡처

### 6.3 호환성 매트릭스 (수동, 릴리스 전)

| 환경 | 확인 항목 |
| --- | --- |
| **Starship** | Nerd Font Symbols 프리셋, Powerline/둥근 구분자(U+E0B0~E0B7) 높이·이음새, 한글 경로(`~/문서/프로젝트`) 표시 |
| **zsh** | Oh My Zsh agnoster, Powerlevel10k `p10k configure` 아이콘 테스트 통과, 자동완성 메뉴 정렬 |
| **iTerm2** | "Use built-in Powerline glyphs" 켬/끔 둘 다, "Ambiguous characters are double-width" 끔, Unicode 9 폭 사용, NFC 정규화 |
| **Linux** | GNOME Terminal(VTE), Konsole, kitty, Alacritty, WezTerm, foot / `fc-match`, `fc-list :spacing=mono`·`dual` 인식, tmux·Neovim 안 정렬 |
| 기타 | macOS Terminal.app, Windows Terminal, VS Code, JetBrains IDE |

---

## 7. 라이선스 (OFL 1.1 준수)

### 7.1 업스트림 RFN 현황 (원문 LICENSE 확인)

| 폰트 | 라이선스 | Reserved Font Name |
| --- | --- | --- |
| JetBrains Mono | OFL 1.1 | 없음 |
| Geist Mono | OFL 1.1 | 없음 |
| 본고딕 / 본명조 (Source Han Sans/Serif) | OFL 1.1 | `Source` (Adobe 상표) |
| Pretendard | OFL 1.1 | `Pretendard`, `Source` (본고딕 파생) |
| IBM Plex Mono | OFL 1.1 | `Plex` |
| 갈무리 (Galmuri) | OFL 1.1 | 없음 (원문 확인) |
| Neo둥근모 / Neo둥근모 Code | OFL 1.1로 알려짐 | **착수 시 원문 확인 필요** |

### 7.2 준수 사항
* 패밀리명·파일명·PostScript명에 RFN 단어를 쓰지 않습니다. RFN이 없는 폰트도 혼동을 피하려고 이름을 바꿉니다("JetBrains"는 상표이기도 함).
* `OFL.txt`에 사용한 모든 업스트림의 Copyright 줄(RFN 문구 포함)을 원문 그대로 남기고, 맨 위에 `Copyright 2026 naturalk (nk-nerd-font)` 를 추가합니다. 포크를 쉽게 하기 위해 본 프로젝트 자체 RFN은 선언하지 않는 것을 권장합니다.
* 폰트 단독 판매 금지, 파생물도 OFL 유지 조건을 README에 명시합니다.
* **Nerd Fonts 아이콘은 세트마다 라이선스가 다릅니다**(OFL, MIT, Apache-2.0, CC BY 4.0 등). Nerd Fonts 레포의 라이선스 목록을 근거로 `LICENSES/` 폴더와 `NOTICE`에 세트별 고지를 넣습니다. "100% OFL"이라고 표기하지 않습니다.
* 업스트림 원본 폰트는 레포에 커밋하지 않고, 버전과 SHA256을 `sources.lock`에 고정해 CI에서 내려받는 방식을 권장합니다(레포 크기와 라이선스 관리 단순화).

---

## 8. 빌드 파이프라인

전 과정을 코드로 제어하며, 가족(Sans/Serif/Pixel)×weight별로 같은 단계를 반복합니다.

1. **fetch:** `sources.lock`에 따라 업스트림 폰트 다운로드, SHA256 검증
2. **subset & convert:** 한글 폰트에서 대상 코드포인트(§3.1 W/F 영역)만 추출, CFF→TrueType(`cu2qu`), UPM 정규화
3. **merge:** 균등 스케일 `s`·오프셋 `dy` 적용, 1200 셀 중앙 정렬 후 영문 TTF에 주입 (fontTools, 영문 GSUB/GPOS 보존)
4. **name & metrics:** name 테이블(패밀리·RIBBI·nameID 16/17, 버전), 세로 메트릭 확정 (§3.3)
5. **patch:** Nerd Fonts 패처 2회 (`Nerd Font`, `Nerd Font Mono`)
6. **finalize:** §3.4 플래그 재적용, 힌팅(§3.7 결정안), WOFF2 생성
7. **pixel export (Pixel 가족만):** BDF/PCF, 마인크래프트 리소스팩, BMFont, 테라리아 XNB 빌드
8. **QA:** §6.1 자동 검사, 교정 시트 렌더링
9. **release (태그 푸시 시):** GitHub Releases 업로드(zip에 `OFL.txt`, `NOTICE`, `LICENSES/` 포함), Homebrew tap·Scoop bucket 해시 갱신 PR 자동 생성

### 8.1 디렉터리 구조

```text
nk-font-r1/
├── .github/workflows/
│   ├── build.yml                 # PR마다 빌드 + QA + 교정 시트
│   └── release.yml               # 태그 푸시 시 릴리스·패키지 갱신
├── config/
│   ├── families/
│   │   ├── sans.toml             # 베이스 폰트, weight 매핑, s/dy, 이름
│   │   ├── serif.toml
│   │   └── pixel.toml            # 격자, 출력 포맷, 배율
│   └── ranges.toml               # 주입 코드포인트 범위 (W/F 영역)
├── sources.lock                  # 업스트림 폰트 URL·버전·SHA256, 패처 이미지 태그
├── pixel-src/                    # 픽셀 마스터 (비트맵 원본/수정분)
├── scripts/
│   ├── fetch_sources.py
│   ├── merge_hangul.py           # subset·cu2qu·스케일·주입
│   ├── set_names_metrics.py
│   ├── fix_flags.py              # §3.4
│   ├── export_pixel.py           # BDF/PCF, unihex, BMFont, 마인크래프트 팩
│   └── build.sh                  # 전체 파이프라인 (Docker 패처 호출 포함)
├── tests/
│   ├── test_widths.py            # wcwidth 전수 검사
│   ├── test_metrics.py
│   └── proofs/                   # 교정 시트 텍스트
├── examples/                     # 마인크래프트 리소스팩, 테라리아 예제, 터미널 설정 예시
├── docs/
├── LICENSES/                     # 업스트림·아이콘 세트별 라이선스 원문
├── OFL.txt
├── NOTICE
└── README.md
```

### 8.2 배포
* **macOS:** `brew install --cask naturalkei/tap/font-nk-mono-nerd-font` (자체 tap `naturalkei/homebrew-tap`)
* **Windows:** `scoop bucket add nk https://github.com/naturalkei/scoop-bucket` → `scoop install nk-mono-nerd-font`
* **Linux:** 릴리스 zip을 `~/.local/share/fonts`에 풀고 `fc-cache -fv`. 이후 AUR 패키지 검토
* **게임용:** 릴리스에 `nk-pixel-minecraft-pack.zip`, `nk-pixel-bmfont.zip`, `nk-pixel-terraria.zip` 별도 첨부

---

## 9. 로드맵

| 단계 | 산출물 |
| --- | --- |
| **M0 기반** | 파이프라인 골격, `sources.lock`, 폭·메트릭 자동 검사, 교정 시트 |
| **M1 Sans MVP** | NK Mono Regular/Bold, Nerd Font + Nerd Font Mono, 호환성 매트릭스 1회 통과, GitHub Release |
| **M2 Sans 정식** | 전체 weight + Italic, 힌팅 결정, Homebrew·Scoop |
| **M3 Pixel** | 16px 마스터, TTF/BDF/PCF, 마인크래프트 리소스팩, BMFont, 테라리아 XNB |
| **M4 Serif** | NK Mono Serif (Plex Mono + 본명조), 작은 크기 weight 보정 |
| **M5 확장** | 조합형 자모(NFD) 지원, 한자 KS X 1001, 픽셀 아이콘 리드로잉, 11px 픽셀 변형, 가변 폰트 검토 |

Pixel을 Serif보다 앞에 둔 이유: Serif는 Sans 파이프라인을 거의 그대로 재사용하는 반면, Pixel은 출력 포맷이 완전히 달라 일찍 검증할수록 위험이 줄어듭니다. 순서는 바꿀 수 있습니다.

---

## 10. 결정이 필요한 사항

1. 패밀리명: `NK Mono` / `NK Mono Serif` / `NK Pixel` 안으로 갈지
2. Sans 한글 베이스: 본고딕 KR(추천) vs Pretendard
3. Pixel 베이스: Neo둥근모 Code(16px, Unifont·마인크래프트 격자와 일치) vs 갈무리(11px 중심)
4. 로드맵 순서: Pixel(M3) → Serif(M4) 순서 유지 여부
5. 업스트림 폰트를 레포에 커밋하지 않고 CI에서 내려받는 방식 동의 여부
