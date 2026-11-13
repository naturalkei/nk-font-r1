# NK Mono 에디터 및 터미널 설정 가이드

NK Mono는 영문 1칸, 한글 2칸(1:2 비율), Nerd Fonts 아이콘이 한 글꼴 파일 안에 일체형으로 통합되어 있어, 별도의 한글 fallback 폰트 설정 없이 단일 폰트 설정만으로 깨짐 없는 개발 환경을 제공합니다.

---

## 1. VS Code (Visual Studio Code)

`Cmd + ,` (macOS) 또는 `Ctrl + ,` (Windows/Linux)를 누른 뒤 `settings.json`을 열어 아래 내용을 추가합니다:

```json
{
  // 1. 폰트 패밀리 지정 (영문과 한글이 모두 NK Mono에서 렌더링됩니다)
  "editor.fontFamily": "'NK Mono', monospace",
  
  // 2. 권장 폰트 크기 및 줄 간격
  "editor.fontSize": 14,
  "editor.lineHeight": 24,

  // 3. 프로그래밍 리거처 활성화 (화살표, 비교 연산자 등)
  "editor.fontLigatures": true,

  // 4. 터미널 내 폰트 설정 (Nerd Fonts 아이콘 포함)
  "terminal.integrated.fontFamily": "NK Mono",
  "terminal.integrated.fontSize": 13,
  "terminal.integrated.lineHeight": 1.2
}
```

---

## 2. iTerm2 (macOS)

1. **Preferences (`Cmd + ,`) → Profiles → Text** 탭으로 이동합니다.
2. **Font** 항목에서 `NK Mono` (Regular 또는 Medium 권장), 크기 `14pt`를 선택합니다.
3. **Use a different font for non-ASCII text** 옵션:
   * **반드시 체크 해제(OFF)** 합니다. (NK Mono 내부에 D2Coding 기반 한글이 이미 최적의 크기와 위치로 내장되어 있으므로 체크할 필요가 없습니다).
4. **Use Ligatures**: 리거처를 보려면 체크합니다.

---

## 3. WezTerm

`~/.wezterm.lua` 파일에 다음과 같이 구성합니다:

```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()

config.font = wezterm.font_with_fallback({
  { family = 'NK Mono', weight = 'Regular' },
})

config.font_size = 14.0
config.line_height = 1.2

-- 리거처 및 사선 0 활성화
config.harfbuzz_features = { 'calt=1', 'zero=1' }

return config
```

---

## 4. Alacritty

`~/.config/alacritty/alacritty.toml` 설정:

```toml
[font]
size = 14.0

[font.normal]
family = "NK Mono"
style = "Regular"

[font.bold]
family = "NK Mono"
style = "Bold"

[font.offset]
x = 0
y = 0
```

---

## 5. Windows Terminal (윈도우 터미널)

`settings.json` 파일의 `profiles.defaults` 블록에 추가합니다:

```json
{
  "profiles": {
    "defaults": {
      "font": {
        "face": "NK Mono",
        "size": 11,
        "features": {
          "calt": 1,
          "zero": 1
        }
      }
    }
  }
}
```

---

## 6. Neovim (Neovide / GUI)

`init.lua`에 설정:

```lua
-- Neovide GUI 환경
if vim.g.neovide then
  vim.o.guifont = "NK Mono:h14"
end
```
(터미널 Neovim의 경우 터미널 에뮬레이터의 폰트를 `NK Mono`로 설정하면 자동 적용됩니다.)
