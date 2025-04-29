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


# alias
alias ls="eza"
alias top="zenith"
alias cat="bat"