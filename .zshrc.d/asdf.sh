# asdf 설정
_asdf_prefix="/opt/homebrew/opt/asdf"
if [ -f "${_asdf_prefix}/libexec/asdf.sh" ]; then
  . "${_asdf_prefix}/libexec/asdf.sh"
fi
unset _asdf_prefix