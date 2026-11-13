# NK Mono OpenType 피처 & 스타일 세트 가이드

NK Mono는 JetBrains Mono의 풍부한 OpenType 피처를 100% 보존하고 있습니다. 한글 글리프 병합 시에도 라틴 영역의 GSUB/GPOS 테이블을 바이트 단위로 보존하여, 프로그래밍 리거처(합자)와 다양한 글자 변형 기능을 그대로 사용할 수 있습니다.

---

## 1. 주요 OpenType 기능 요약

| Feature 태그 | 기능 명칭 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `calt` | Contextual Alternates | On (켜짐) | `->`, `=>`, `===`, `!=`, `<!--` 등 프로그래밍 연산자 및 화살표 합자 (고정폭 격자 준수) |
| `zero` | Slashed Zero | Off (꺼짐) | 숫자 0 내부에 사선(/)을 그어 대문자 O와의 구별성을 극대화 |
| `ss01` | Stylistic Set 1 | Off | 단층 소문자 a (`ɑ`) 형태 적용 |
| `ss02` | Stylistic Set 2 | Off | 단층 소문자 g 형태 적용 |
| `ss03` | Punctuation Ligatures | Off | `;;`, `;;;`, `::`, `:::`, `...`, `!!` 등 기호 반복 시 압축 합자 (기본 calt에서 격자 보호를 위해 분리됨) |
| `ss19` / `ss20` | Ligature Control | Off | 특정 특수 기호 합자 선택적 활성화/비활성화 |
| `cv01` ~ `cv20` | Character Variants | Off | 특정 글리프(소문자 l, 1, f, j, k, r, t 등)의 대체 디자인 |

---

## 2. 에디터 및 개발 환경별 설정법

### 1) VS Code (`settings.json`)

```json
{
  "editor.fontFamily": "'NK Mono', monospace",
  "editor.fontSize": 14,
  "editor.lineHeight": 1.6,
  
  // 1. 프로그래밍 리거처 기본 활성화
  "editor.fontLigatures": true,

  // 또는 2. 리거처를 켜면서 사선 0(zero) 및 단층 a(ss01) 적용 시:
  // "editor.fontLigatures": "'calt' on, 'zero' on, 'ss01' on",

  // 3. 리거처를 완전히 끄고 일반 폰트처럼 쓸 때:
  // "editor.fontLigatures": false
}
```

### 2) WezTerm (`wezterm.lua`)

```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()

config.font = wezterm.font({
  family = 'NK Mono',
  harfbuzz_features = { 'calt=1', 'zero=1' },
})
config.font_size = 14.0

return config
```

### 3) Alacritty (`alacritty.toml`)

Alacritty는 FreeType/HarfBuzz를 통해 기본적으로 `calt`를 렌더링합니다:

```toml
[font]
size = 14.0

[font.normal]
family = "NK Mono"
style = "Regular"

[font.bold]
family = "NK Mono"
style = "Bold"
```

### 4) Neovim (GUI: Neovide / MacVim)

```lua
-- init.lua (Neovide)
vim.o.guifont = "NK Mono:h14"
```

---

## 3. 대표 프로그래밍 리거처 샘플

NK Mono에서 기본 지원하는 주요 리거처 조합입니다:

* 화살표: `->`, `-->`, `=>`, `==>`, `<-`, `<--`, `<->`, `<=>`
* 비교 및 논리: `==`, `===`, `!=`, `!==`, `<=`, `>=`, `=~`, `!~`
* 연산 및 파이프: `|>`, `<|`, `||`, `&&`, `++`
* 웹 및 마크업: `</`, `/>`, `<!--`, `-->`
* 주석 및 태그: `/*`, `*/`, `///`, `##`

---

## 4. 기호 반복 합자(ss03) 분리 안내

JetBrains Mono 원본에서는 세미콜론(`;;`), 콜론(`::`), 마침표(`..`, `...`), 느낌표(`!!`), 물음표(`??`) 등을 연속 입력했을 때 이를 좁은 폭(~440 UPM)으로 압축하는 합자가 기본 `calt`에 포함되어 있었습니다. 이로 인해 4글자 이상 연속 입력 시 일부만 합자로 묶이고 나머지는 단독 글리프로 남아 터미널/에디터의 1:1 고정폭 셀 격자 정렬이 어긋나는 문제가 있었습니다.

NK Mono는 엄격한 터미널 모노스페이스 정렬을 위해 이 압축 합자들을 기본 `calt`에서 제외하고 **`ss03` (Punctuation Ligatures)** 기능으로 분리하였습니다:
- **기본 상태 (`calt` 켜짐, `ss03` 꺼짐)**: 모든 연산자 합자(`!=`, `===`, `=>` 등)는 작동하되, 세미콜론·마침표 등 기호는 정확히 1:1 격자 중앙(600 UPM)에 균일하게 배치됩니다.
- **`ss03` 활성화 시**: 기호 반복 입력 시 좁아지는 JetBrains Mono 특유의 압축 합자 스타일을 선택적으로 적용할 수 있습니다.
  - VS Code: `"editor.fontLigatures": "'calt' on, 'ss03' on"`

