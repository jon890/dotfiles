# SSH 에이전트 자동 설정
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)" > /dev/null
fi

# SSH 키들을 자동으로 로드 (키체인에서)
ssh-add --apple-load-keychain 2>/dev/null

# NHN 게이트웨이 SSH 유틸리티 로드
[[ -f "$HOME/.config/nhn-ssh/nssh.sh" ]] && source "$HOME/.config/nhn-ssh/nssh.sh"
