# kube-ps1: kubectl context/namespace 프롬프트 표시
if (( ${+commands[brew]} )) && [[ -f "$(brew --prefix kube-ps1 2>/dev/null)/share/kube-ps1.sh" ]]; then
  source "$(brew --prefix kube-ps1)/share/kube-ps1.sh"

  # 스타일 설정
  KUBE_PS1_SYMBOL_ENABLE=true
  KUBE_PS1_SYMBOL_DEFAULT="⎈"
  KUBE_PS1_PREFIX="%F{blue}(%f"
  KUBE_PS1_SEPARATOR="%F{white}·%f"
  KUBE_PS1_SUFFIX="%F{blue})%f"
  KUBE_PS1_CTX_COLOR=cyan
  KUBE_PS1_NS_COLOR=green

  # PS1 앞에 kube_ps1 삽입
  # $'\n$(kube_ps1) ' → ANSI-C 쿼팅으로 실제 newline + 리터럴 $(kube_ps1)
  # promptsubst가 렌더링 시 $(kube_ps1)을 평가함
  PS1=$'\n$(kube_ps1) '"${PS1#$'\n'}"
fi
