# SSH 에이전트 자동 설정
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)" > /dev/null
fi

# SSH 키들을 자동으로 로드 (키체인에서)
ssh-add --apple-load-keychain 2>/dev/null
