# NK 가족 기획: Mono · Sans · Novel · Comics (+ 차별화·굵기·기능 체계)

> 2026-11-02 · 기준 문서: [PLAN.md](PLAN.md), [ROADMAP.md](ROADMAP.md)
> 요청: NK Mono, NK Novel(책·소설·뉴스/신문 읽기 전용), NK Comics 추가. 대중적인 폰트와 뚜렷이 다른 특색,
> 황금비율 메커니즘, 인쇄 디자인에서 쓸 수 있는 굵기 범위, 게임 개발자를 위한 픽셀 터미널 스타일.
> MonoLisa 3.0(Code/Text 서브패밀리 분리, GRAD 축, ss/cv/dlig 정리)은 **구성의 참고**로만 쓰고, 이름·기능 배치·디자인은 NK 고유의 것으로 만듭니다.

---

## 1. 여섯 가족 한눈에

> 2026-11-02 재편(사용자 결정): **NK Sans는 처음부터 고정폭일 이유가 없는 문서용 비례폭 고딕**으로 바꾸고, 터미널 대표 역할은 **NK Mono**가 맡습니다. NK Mono 한글은 사용자가 좋아하는 D2Coding의 한글을 씁니다. NK Comics는 "더 과장되고 만화다운" 레터링으로 다시 짰습니다.
>
> 2026-11-03: **NK Serif도 문서용 비례폭 명조**(IBM Plex Serif + 본명조)로 전환했습니다. 터미널 갈래는 NK Mono와 NK Pixel 두 가족입니다.

NK는 두 갈래입니다. **터미널 갈래**는 1 : 2 셀 격자(0 / 600 / 1200)와 Nerd 아이콘을 지키는 고정폭, **문서·읽기 갈래**는 격자 없이 사람이 읽는 비례폭입니다. MonoLisa 3.0이 Code와 Text를 나눈 것과 같은 방향이지만, NK의 비례폭 갈래는 한글 본문이 주인공입니다.

| 가족 | 갈래 (`kind`) | 용도 | 영문 베이스 | 한글 베이스 | 기본 줄 높이 |
| --- | --- | --- | --- | --- | --- |
| **NK Mono** | 터미널 (`merge`) | 터미널·코딩 대표 | JetBrains Mono | **D2Coding 한글** (RFN `D2Coding`) | 영문 베이스 1.32 (불변) |
| NK Pixel | 터미널 (`pixel`) | 픽셀 터미널 + 게임 | Neo둥근모 Code | Neo둥근모 Code | 픽셀 격자 |
| **NK Sans** | 문서 (`text`) | 일반 문서·UI·발표 자료 | **IBM Plex Sans** | 본고딕 KR | φ^5/6 = 1.493 |
| **NK Serif** | 문서 (`text`) | 보고서·논문·편지·인쇄물 | **IBM Plex Serif** | 본명조 KR (한 단계 굵게) | φ^5/6 = 1.493 |
| **NK Novel** | 읽기 (`text`) | 책·소설·뉴스·신문 본문 | Crimson Text | 고운바탕 | φ = 1.618 |
| **NK Comics** | 읽기 (`text`) | 만화·웹툰 말풍선·효과음 | **Bagel Fat One / Gasoek One** | 같은 소스 + 본고딕 Heavy 보충 | √φ = 1.272 |

라이선스는 모두 2026-11-02에 업스트림 원문으로 확인해 `sources.lock`에 고정했습니다. RFN이 있는 소스(`D2Coding`, `Plex`, `Source`, `Neo둥근모`, 비교용 `물마루`)는 `RESERVED_NAMES`가 이름 사용을 막습니다. Crimson Text, 고운바탕, Bagel Fat One, Gasoek One, JetBrains Mono는 RFN이 없습니다.

### 1.1 NK Mono: 터미널 대표
* **영문**: JetBrains Mono. 합자와 cv/ss 기능을 그대로 두고, 합자를 싫어하는 사용자는 `calt`를 끄면 됩니다.
* **한글**: D2Coding 한글(나눔바른고딕 기반, 1 : 2 고정폭용). 비례폭 본고딕을 줄여 넣던 이전 Sans보다 두 칸을 꽉 채우고 획이 단정합니다(스케일 1.08, dy +40).
* D2Coding에서 참고할 점: 비슷한 글자(`0 O ㅇ`, `1 l I |`, `ㅡ -`)의 구별을 최우선으로 한 설계 원칙. NK 제로·문장부호 기능(§2)이 이 원칙을 이어받습니다. D2Coding 영문은 쓰지 않으므로 NK Mono가 D2Coding의 이름 바꾼 복제가 되지 않습니다.

### 1.2 NK Sans: 문서용 고딕
* IBM Plex Sans(정적 100–700, 인쇄용 굵기 확장에 유리) + 본고딕 KR(7단계). 한글 스케일 0.90, 자간 −20.
* 기본 줄 높이 φ^5/6 = 1.493: 문서 본문에 흔히 쓰는 1.5와 거의 같으면서 공용 φ 스케일(step 5)에 맞습니다.
* 소개 사이트의 UI 글꼴로도 직접 씁니다.

### 1.3 NK Novel과 NK Comics
* **Novel**: 고운바탕(11,172자) + Crimson Text. 한글 스케일 0.92, 자간 −10, 줄 높이 φ.
* **Comics**: 통통 튀는 **Bagel Fat One**(Regular)과 굵게 외치는 **Gasoek One**(Black). 둘 다 같은 디자이너(JAMO Typeface)가 영문과 한글을 함께 그려 과장된 만화 레터링이 한 몸으로 맞습니다. 원본은 2,780음절이라 나머지 8,389음절은 본고딕 Heavy를 크기 맞춰 보충해 글자가 빠지지 않게 했습니다(드문 글자만 해당, 이후 원본 스타일로 다시 그리기 과제). 줄 높이 √φ.
  * 비교 레퍼런스: **만화진흥원체(KOMACON, 한국만화영상진흥원)**. 받은 배포본에 읽을 수 있는 라이선스 전문이 없어 재배포 가능 여부를 확인할 수 없으므로, 레포에 커밋하거나 `sources.lock`에 고정하지 않고 `config/local_fonts.toml`에 **로컬 전용**으로 등록했습니다. 공식 설치본(KomaconFonts.dmg/.exe)으로 설치하면 `KOMACON.ttf`를 `~/Library/Fonts` 등에서 찾아 글리프 랩(`/lab`, `/lab/advanced`, `/presets`)에 비교용으로 띄웁니다(`sources/local/` 또는 `$NK_LOCAL_FONTS`에 둬도 됨). 측정·표시만 하고 병합·사이트 배포는 하지 않습니다.
  * 필기체 방향 레퍼런스(2026-11-03, 사용자가 HCL 리얼노트필기 같은 펜 필기 느낌을 원함, 디자인 변경 전): **개구 Gaegu**(OFL, RFN 없음, Light/Regular/Bold, 2,350음절)와 **나눔손글씨 펜**(OFL, RFN `Nanum`, 11,172음절)은 `sources.lock`에 고정하고 글리프 랩에 추가했습니다. **HCL 리얼노트필기**는 라이선스를 찾지 못해 `config/local_fonts.toml`에 로컬 전용으로 두고, 설치 파일명을 몰라 `HCL*리얼노트*`, `*RealNote*` 패턴으로 찾습니다. 모두 모양 참고용이며 글리프를 가져오지 않습니다.

### 1.4 NK Pixel과 "mono-pixel" 터미널 스타일
요청하신 게임 개발자용 mono-pixel 터미널 스타일은 **NK Pixel에 통합**합니다. NK Pixel은 이미 반각 8×16 / 전각 16×16 격자의 터미널 폰트이고 Nerd Font / Nerd Font Mono로 패치됩니다. 별도 가족을 만들면 같은 픽셀 마스터를 두 번 관리하게 되므로, 대신 NK Pixel 안에서 터미널 완성도를 높입니다.
* Powerline 구분자(U+E0B0–E0B3)와 Starship·p10k 상위 아이콘 100개를 **픽셀로 다시 그려** 벡터 아이콘이 섞이지 않게 함 (M3)
* 박스·블록 문자(U+2500–259F)를 8×16 격자에 정확히 맞춘 픽셀 버전으로 교체, 셀 경계 이음새 0
* 게임 개발 화면을 위한 샘플: 타일맵 좌표, HP/MP 바(블록 문자), 대화창 테두리
* 출력: 터미널 TTF + BDF/PCF + 마인크래프트 unihex + BMFont, 같은 마스터에서 생성

---

## 2. 차별화: "대중적인 폰트와 단연 다른" NK 시그니처

JetBrains Mono, D2Coding, Sarasa Mono K와 나란히 놓았을 때 NK만의 것으로 보여야 할 요소입니다. 베이스 폰트를 합치는 데서 멈추지 않고, **한글 터미널·한글 읽기에서만 생기는 문제를 기능으로 푸는 것**을 NK의 정체성으로 삼습니다.

| 시그니처 | 내용 | 대상 | 시점 |
| --- | --- | --- | --- |
| **φ 비례 체계** | 한글 높이·폭·획, 줄 높이까지 φ 거듭제곱 목표로 맞추고 리포트로 증명 (§3) | 전 가족 | 이번 PR(줄 높이), 조정 도구 스레드(나머지) |
| **한글 정렬 보증** | wcwidth와 advance 전수 대조, 잉크 넘침 0, 골든 이미지 회귀. 사이트에 격자 오버레이로 증명 | 터미널 | 구현됨 |
| **받침 기준선 규칙** | 받침 유무에 따라 한글 dy를 미세 보정해 영문 대문자 중심과 광학 정렬 | Sans·Serif·Mono | M2 |
| **NK 제로** | 한글 `ㅇ`과 구별되는 0: 점 대신 짧은 사선, 터미널에서 `0`/`O`/`ㅇ` 3중 구분 | 터미널 | M2 (영문 소스 cv 위에 NK 글리프) |
| **한글 문장부호 정렬** | `「」『』·…`를 한글 중심선에 맞춘 대체형, 터미널에서는 셀 중앙 | 전 가족 | M2 |
| **읽기 갈래의 φ 행간** | 앱 설정 없이도 본문 1.618, 말풍선 1.272 | Novel·Comics | 이번 PR |
| **픽셀 Powerline** | 픽셀로 다시 그린 Powerline·아이콘 | Pixel | M3 |

### 2.1 NK OpenType 기능 체계 (계획)
MonoLisa의 목록은 참고만 하고 번호와 이름은 NK 기준으로 새로 짭니다. 원칙: **기본값은 터미널에서 안전한 쪽**, 한글 관련 기능은 NK 고유 번호대(`ss11`~)에 모읍니다.

| 기능 | 내용 | 기본 | 가족 |
| --- | --- | --- | --- |
| `calt` | 영문 문맥 대체 (베이스에서 보존) | 켜짐 | Mono |
| `dlig` | 코딩 합자 전체를 한 번에 (`->`, `=>`, `!=`, `===`) | 꺼짐 | Mono |
| `zero` | NK 제로 (사선) | 꺼짐 | 전 가족 |
| `tnum` / `pnum` | 고정 숫자 / 비례 숫자 | Novel은 `pnum`, 터미널은 고정 | 전 가족 |
| `onum` / `lnum` | 올드스타일 / 라이닝 숫자 | Novel 본문 `onum` 검토 | Novel |
| `frac` | 분수 | 꺼짐 | Novel·Sans |
| `ss01` | 대체 `g`·`@`·`&` 묶음 (코딩 취향) | 꺼짐 | 터미널 |
| `ss02` | 대체 `{}`·`()` | 꺼짐 | 터미널 |
| `ss11` | **한글 문장부호 중앙 정렬** (`「」『』…·`) | 꺼짐 | 전 가족 |
| `ss12` | **받침 기준선 보정 강하게** (제목용) | 꺼짐 | Sans·Novel |
| `ss13` | **세로쓰기 문장부호** (Novel `vert` 보완) | 꺼짐 | Novel |
| `ss14` | **효과음 굵게** (말풍선 의성어·의태어용 대체형) | 꺼짐 | Comics |

`dlig`/`ss` 구현은 영문 베이스의 GSUB를 보존한 위에 NK 글리프와 룩업을 추가하는 방식(fontTools feaLib)이며, 각 기능은 QA에 "기능 켜고 렌더 → 골든 비교" 단계를 같이 넣습니다.

---

## 3. 황금비율(φ) 메커니즘

모든 의도적 비율을 φ의 거듭제곱으로 정합니다. 조정 도구 스레드가 가족 공용 `config/proportions.toml`(목표 = φ^(단계/6))과 `nkfont phi` 리포트를 만들고 있고, 새 가족도 같은 파일을 씁니다. 이번 PR은 그중 **줄 높이 규칙**을 구현했습니다.

| 비율 | 값 | 스케일 단계 (φ^(n/6)) | 쓰임 |
| --- | --- | --- | --- |
| φ¹ | 1.618 | 6 | NK Novel 기본 줄 높이 |
| φ^½ | 1.272 | 3 | NK Comics 기본 줄 높이 |
| φ^(2/6) | 1.174 | 2 | 한글 높이 / 영문 대문자 높이 (조정 도구 규칙) |
| φ^(−1/6) | 0.923 | −1 | 한글 획 / 영문 획, 한글 잉크 종횡비 (조정 도구 규칙) |
| φ^(−5/6) | 0.670 | −5 | 한글 잉크 폭 / 두 칸 폭 (터미널) |

* 설정: `[metrics] line_height = "phi"` 또는 `"phi^0.5"` (숫자도 가능). `src/nkfont/phi.py`가 해석하고, ascent와 descent는 그대로 둔 채 남는 공간을 `lineGap`으로 넣어 `ascent − descent + lineGap = round(φ·UPM)`이 정확히 성립합니다. 실제 빌드: NK Novel 983 + 307 + 367 = 1657 / 1024 = 1.618, NK Comics 932 + 340 = 1272 / 1000.
* 터미널 가족은 φ로 줄 높이를 바꾸지 않습니다. 터미널은 줄 높이로 셀 높이를 정하고 Powerline 이음새가 걸려 있어, 영문 베이스 메트릭 유지가 불변 규칙입니다(조정 도구도 이 규칙들은 `locked`로 표시만).

---

### 3.1 레퍼런스 기반 변형 프리셋 (가족마다 20종)

`config/presets/`의 프리셋은 빌드 입력이 아니라 `/presets`에서 나란히 비교하는 후보입니다. 레퍼런스 글꼴은
**재기만 하고** 글리프는 가져오지 않습니다. 모든 값은 우리 조절값으로만 만듭니다.

| 가족 | 레퍼런스 | 조절 축 | 20종의 방향 |
| --- | --- | --- | --- |
| NK Mono | JetBrains Mono(영문), D2Coding(한글 원본) | `[hangul]` scale·dy·width·grade·center + JetBrains Mono 기능(ss01, ss02, zero, cv01, cv04) | 높이·폭·획·중심 목표(φ 정합, D2Coding에서 잰 비례, 대문자 중심, 획 일치 등)를 Glyph Lab 솔버로 풀어 만든 값. Bold 3종 |
| NK Pixel | Neo둥근모(원본), 물마루 | `[pixel]` bold(-1/+1px)·italic(N줄마다 1px)·shadow·hangul_dy·dy/scope | 1px 가는 획, 볼드, 계단 이탤릭 3단계, 게임 UI 그림자, 한글 1px 올림(대문자 중심 맞춤)과 그 조합 |
| NK Comics | 개구, 나눔손글씨 펜, 만화진흥원체(로컬), HCL 리얼노트필기(로컬) | `[style]` slant·grade·tracking·bounce·tilt·seed (영문과 한글을 함께) | 펜 필기 14종(마커·사인펜·볼펜·만년필·노트·일기·붓펜 등: 획을 깎고 기울이고 글자마다 기준선·각도를 흔듦) + 레터링 6종(외침·효과음·포스터 등, Black 포함) |
| NK Sans | IBM Plex Sans(원본), 본고딕(원본), **Pretendard**, **IBM Plex Sans KR**, **고딕 A1**, **Inter**(영문) | `[hangul]` scale·dy·width·grade·tracking + `[style]` slant·grade·tracking | 레퍼런스 실측 비율(Pretendard, Plex Sans KR, 고딕 A1의 한글 높이·중심·획·자간)을 솔버로 역산 + φ 정합, 헤드라인·캡션·좁은/넓은 한글·가는/진한 본문·오블리크 등 |
| NK Serif | IBM Plex Serif(원본), 본명조(원본), **나눔명조**, **함렛 Hahmlet**, **Source Serif 4**(영문), 마루 부리(로컬) | 위와 같음 + `stem` | 나눔명조·함렛 실측 비율, 본명조 원본, φ, 보고서·편지·다단·제목·화면 명조 등. Bold는 세로획(`stem`)으로 채워 명조 대비를 지킴 |
| NK Novel | Crimson Text·고운바탕(원본), **송명**, **나눔명조**, **Crimson Pro**·**Literata**·**EB Garamond**(영문), KoPubWorld 바탕(로컬) | 위와 같음 + `stem` | 고운바탕 원본·송명·나눔명조 실측 비율, φ, 전자책·문고본·양장본·신문·시집·동화책·큰글씨책 등 |

**조화 QA**: `nkfont presets`가 프리셋마다 한글과 영문의 높이·중심·획 굵기·대비·회색도·기울기·자간과 격자를
재고 `config/preset_qa.toml` 밴드를 벗어나면 실패합니다(qa 단계 "preset harmony"). QA가 정한 한계:

- Comics(Bagel Fat One)는 grade -95보다 더 깎으면 한글 획이 영문보다 너무 가늘어지고(획 0.84 미만) 윤곽이 뒤집힙니다.
  더 가는 진짜 펜 느낌은 펜 필기 원본(예: 개구, OFL)으로 Comics 소스를 바꾸는 결정이 필요합니다.
- Comics Black(Gasoek One)은 원래 한글 획이 영문보다 가벼워(0.85) 깎을 여유가 없습니다.
- NK Novel(고운바탕 + Crimson Text)은 한글 획이 영문의 0.725로 너무 가늘었습니다. `grade`만 올리면 고운바탕의
  가로획까지 굵어져 대비가 밴드를 넘으므로, 세로획만 굵히는 새 `[hangul] stem`(FreeType EmboldenXY 방식,
  기본 0 = 항등)을 더해 저장값을 scale 0.9 · grade 8 · stem 14로 바꿨습니다(획 0.924 ≈ φ^(−1/6), 대비 1.07).
- Sans·Serif의 Bold 저장값은 한글 획이 영문 Bold보다 가볍습니다(Sans 0.80, Serif 0.67; 저장값 비교는 Regular만
  경고 대상). Bold 프리셋은 grade·stem으로 0.88 이상을 맞췄고, 저장값 자체는 굵기별 `[hangul]`이 생길 때 다룹니다.
- Pixel의 가로획 2px(`heavy`)과 블랙은 16px 한글에 자리가 없어 를·를 가로획 사이 1px 틈이 막히거나 영문만 굵어져
  밴드를 벗어납니다. 축은 남기고 프리셋에서는 뺐습니다.

## 4. 인쇄 디자인용 굵기 범위

목표: 인쇄 디자이너가 제목부터 각주까지 한 가족으로 쓸 수 있도록 **Thin(100)부터 Black(900)까지 9단계 + 이탤릭**, 가변 폰트(`wght` 축)와 정적 OTF/TTF를 함께 제공합니다. 굵기 이름, `usWeightClass`, 스타일 링크(RIBBI는 같은 패밀리, 나머지는 `NK Sans Light` 같은 레거시 패밀리 + `typographic family` 16/17번)는 이미 `names.py`가 규칙대로 씁니다.

| 가족 | 영문 소스 굵기 | 한글 소스 굵기 | 1.0 목표 | 메모 |
| --- | --- | --- | --- | --- |
| NK Sans | IBM Plex Sans 100–700 + 이탤릭 | 본고딕 7단계 (ExtraLight–Heavy) | 100–900, 이탤릭, 가변 | 인쇄용 대표. Plex 7단계와 본고딕 7단계를 1:1로 짝짓고 800–900은 본고딕 Bold/Heavy + 영문 보간 |
| NK Serif | IBM Plex Serif 100–700 (7) + 이탤릭 | 본명조 7단계 (ExtraLight–Heavy) | 100–900, 이탤릭 | 명조는 한 단계 올려 매핑. NK Sans와 같은 Plex 뼈대라 굵기 단계도 짝이 맞음 |
| NK Mono | JetBrains Mono 100–800 + 이탤릭 | D2Coding 2단계 | Regular·Bold → 4단계 이상 | D2Coding 한글이 2단계뿐이라 Light·ExtraBold는 획 굵기 보간(조정 도구의 grade) 필요 → M5 |
| NK Novel | Crimson Text 400/600/700 + 이탤릭 (가변 Crimson Pro 200–900) | 고운바탕 2단계 | 300–800 | 한글 굵기 확장이 병목: 고운바탕 가변화 또는 본명조 계열 대체 검토 |
| NK Comics | Bagel Fat One / Gasoek One | 같은 소스 | Regular·Black (+ 기울임 효과음) | 레터링 글꼴이라 굵기보다 "목소리"(대사·외침·속삭임)로 나눔 |
| NK Pixel | 단일 | 단일 | Regular (+ 픽셀 Bold) | 픽셀은 1 px 두께 증가로 Bold 생성 |

인쇄용 출력 형식: 정적 OTF(CFF, 인쇄 RIP 호환) + TTF + 가변 TTF + WOFF2. PDF 임베딩 허용(`fsType` = 0, 설치 가능)을 QA에서 검사합니다.

---

## 5. 문자 범위 목표

| 범위 | 터미널 갈래 | 읽기 갈래 |
| --- | --- | --- |
| 현대 한글 11,172자, 호환 자모, 전각·반각 | 필수 (구현됨, QA 검사) | 필수 (구현됨, `hangul-coverage` 검사) |
| 라틴 확장 A/B·추가, 그리스, 키릴 | 영문 소스 범위 그대로 | 영문 소스 범위 그대로 |
| 박스·블록·Powerline, Nerd 아이콘 | 필수 | 해당 없음 |
| 한자 KS X 1001 4,888자 | M5 | Novel M5 (신문 본문 필요) |
| 옛한글·조합형 자모 | M5 (ljmo/vjmo/tjmo) | M5 |
| 숫자 기능 `tnum` `pnum` `onum` `lnum` `frac` | 계획 (§2.1) | 계획 (§2.1) |

---

## 6. 빌드 파이프라인 변경 (이번 PR)

* `kind = "text"`: 영문 텍스트 폰트에 한글을 병합하되 한글은 **원본 간격을 비례 축소**해 넣습니다(`HangulParams.advance = "proportional"`, `tracking`). 터미널 폭 보정과 Nerd 패치는 하지 않고 `enforce_text_flags`가 고정폭 표시를 끄고 줄 메트릭을 맞춥니다.
* TrueType 한글 소스(D2Coding·고운바탕·Bagel Fat One) 지원: CFF 소스만 윤곽 방향을 뒤집고, 합성 글리프는 분해합니다. 이전에는 모든 소스를 뒤집어 TrueType 소스가 들어오면 윤곽 방향이 거꾸로 됐을 것입니다(합성 폰트 회귀 테스트 추가).
* 보충 병합: 영문 소스에 이미 한글이 있으면(NK Comics) 병합은 없는 음절만 한글 소스에서 채웁니다.
* QA: 읽기 갈래는 폭·잉크 넘침 대신 `text-metrics`(고정폭 표시 금지, hhea = typo, usWin이 bbox 포함), `hangul-coverage`(11,172자), 이름·기능 검사를 돌리고, 골든 이미지는 본문 샘플로 렌더합니다. `nkfont patch`는 터미널 가족만 패치합니다.
* 명령: `nkfont build all`, `nkfont check --kind text`, `nkfont qa --family novel`. `nkfont qa`·`build`·`tune`의 기본 가족은 이제 `mono`입니다.
