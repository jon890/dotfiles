# 기본 Zsh 설정
setopt HIST_IGNORE_ALL_DUPS
bindkey -e
WORDCHARS=${WORDCHARS//[\/]}

# .zshrc.d 설정 로드
if [ -d "${ZDOTDIR:-$HOME}/.zshrc.d" ]; then
  for file in "${ZDOTDIR:-$HOME}/.zshrc.d"/*.sh; do
    if [ -f "$file" ]; then
      source "$file"
    fi
  done
fi

# alias - 조건부 설정 (프로그램이 설치되어 있을 때만)
if command -v eza >/dev/null 2>&1; then
  alias ls="eza"
fi

if command -v zenith >/dev/null 2>&1; then
  alias top="zenith"
fi

if command -v bat >/dev/null 2>&1; then
  alias cat="bat"
fi

# intellij terminal 한글 깨짐 수정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8

# Run fastfetch on terminal startup only if it's installed
if command -v fastfetch >/dev/null 2>&1; then
  fastfetch
fi 
