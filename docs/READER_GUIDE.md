# NK Novel 텍스트 뷰어 & 전자책 독서 가이드

NK Novel은 전통 북디자인 서체인 **Crimson Text**와 현대적인 화면 독서용 명조인 **고운바탕(Gowun Batang)**을 정밀 결합한 장문 읽기 전용 글꼴입니다.

---

## 1. 황금비(φ = 1.618 em) 줄 높이 체계

긴 글을 읽을 때 시선이 다음 줄의 첫머리로 이동하는 과정(Eye Saccade)에서 피로도가 누적됩니다. NK Novel은 폰트 파일 자체 메트릭스(Ascent 960, Descent -300, LineGap)에 황금비율($\phi \approx 1.618$)을 내장하여, 별도의 CSS 행간 설정 없이도 문단이 숨 쉴 수 있는 편안한 여백을 자동으로 형성합니다.

| 메트릭스 속성 | 값 (UPM 1000 기준) | 설명 |
| :--- | :--- | :--- |
| `ascent` | 960 | 글자 상단 기준선 |
| `descent` | -300 | 글자 하단 기준선 |
| `lineGap` | 358 | 황금비(1.618 em = 1618 유닛)를 완성하는 기본 행간 |
| `tracking` | -10 | 한글 글자 사이를 10유닛 좁혀 긴 문장의 글줄 흐름 유지 |

---

## 2. 옵시디언 (Obsidian) 설정법

1. **설정 (`Cmd + ,` 또는 `Ctrl + ,`) → Appearance (외관)** 로 이동합니다.
2. **Font (글꼴)** 섹션의 **Text font (텍스트 글꼴)** 항목에서 `Manage`를 클릭합니다.
3. `NK Novel`을 검색하여 추가하고 최상단으로 지정합니다.
4. (선택 사항) **Line width (줄 너비)**를 700~800px로 제한하면 고전문학 서적과 같은 최상의 독서 경험을 얻을 수 있습니다.

```css
/* snippets/nk-novel-reader.css (선택 적용 가능한 사용자 CSS 스니펫) */
.markdown-rendered, .cm-content {
  font-family: 'NK Novel', serif;
  font-size: 16px;
  line-height: 1.618;
}
```

---

## 3. 전자책 리더 (Apple Books, 리디북스, Calibre)

* **macOS / iOS 도서 (Books)**:
  1. `NKNovel-Regular.ttf` 및 `NKNovel-Bold.ttf`를 서체 관리자(Font Book)에 등록합니다.
  2. 도서 앱 보기 설정(Aa)에서 서체를 `NK Novel`로 선택합니다.
* **리디북스 페이퍼 / 안드로이드 전자책 앱**:
  * 폰/기기의 `Fonts` 폴더에 `NKNovel-*.ttf`를 복사한 뒤 앱 내 '사용자 폰트'로 선택합니다.

---

## 4. 독서 테마별 권장 굵기 가이드

배경 색상에 따른 명암 대비 차이에 따라 획 두께 인지도가 달라집니다:

* **라이트 모드 (흰 배경)**: `Regular (400)` 또는 `Medium (500)` 권장
  * 검은 글자가 밝은 배경 속에서 또렷하게 인식됩니다.
* **세피아 / 크림 모드 (아이보리 배경)**: `Regular (400)` 권장
  * 종이책을 읽는 듯한 가장 눈이 편안한 균형을 제공합니다.
* **다크 모드 (검은 배경)**: `Light (300)` 또는 `Regular (400)` 권장
  * 어두운 배경에서는 빛 번짐(Halation) 현상으로 글자가 두껍게 느껴지므로, 한 단계 가벼운 굵기가 가독성에 좋습니다.
