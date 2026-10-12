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

export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
export PATH="$HOME/.local/bin:$PATH"

# bun completions
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

# zoxide 초기화 (반드시 마지막에 위치해야 함)
if (( ${+commands[zoxide]} )); then
  # zoxide는 .zshrc 최하단에서 초기화되지만, .zshrc.d/ 내 zim/kube-ps1이
  # 먼저 로드되면서 _ZO_DOCTOR 오탐이 발생하므로 진단 비활성화
  export _ZO_DOCTOR=0
  eval "$(zoxide init zsh)"

  # zoxide 별칭 설정
  alias cd="z"
  alias cdi="zi"
fi
