# zoxide 설정
if (( ${+commands[zoxide]} )); then
  eval "$(zoxide init zsh)"
  
  # zoxide 별칭 설정
  alias cd="z"
  alias cdi="zi"
fi 
