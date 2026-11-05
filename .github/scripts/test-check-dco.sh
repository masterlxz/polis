#!/usr/bin/env bash
# Testes do check-dco.sh. Cada caso cria um repositório git temporário, faz
# commits e roda `check-dco.sh <base> <head>`. Uso: .github/scripts/test-check-dco.sh
set -u

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check-dco.sh"
pass=0
fail=0

new_repo() {
  REPO=$(mktemp -d)
  git -C "$REPO" init -q -b main
  git -C "$REPO" config user.name "Ana Autora"
  git -C "$REPO" config user.email "ana@example.com"
  git -C "$REPO" commit -q --allow-empty -m "base (fora do intervalo)"
  BASE=$(git -C "$REPO" rev-parse HEAD)
}

# commit <mensagem> [autor_nome autor_email [committer_nome committer_email]]
# O committer padrão é Ana Autora <ana@example.com> (a identidade do repo).
commit() {
  local msg="$1" name="${2:-Ana Autora}" email="${3:-ana@example.com}"
  local cname="${4:-Ana Autora}" cemail="${5:-ana@example.com}"
  GIT_AUTHOR_NAME="$name" GIT_AUTHOR_EMAIL="$email" \
    GIT_COMMITTER_NAME="$cname" GIT_COMMITTER_EMAIL="$cemail" \
    git -C "$REPO" commit -q --allow-empty -m "$msg"
}

# expect <passa|falha> <descrição> [texto que deve aparecer na saída]
expect() {
  local want="$1" desc="$2" needle="${3:-}" out code
  out=$(cd "$REPO" && "$SCRIPT" "$BASE" HEAD 2>&1)
  code=$?
  local got=passa
  [ "$code" -ne 0 ] && got=falha
  if [ "$got" = "$want" ] && { [ -z "$needle" ] || grep -qF -- "$needle" <<<"$out"; }; then
    pass=$((pass + 1)); echo "ok    - $desc"
  else
    fail=$((fail + 1)); echo "FALHOU - $desc (esperado: $want; obtido: $got; saída: $out)"
  fi
  rm -rf "$REPO"
}

new_repo
commit $'Adiciona X\n\nSigned-off-by: Ana Autora <ana@example.com>'
expect passa "commit com sign-off do próprio autor passa"

new_repo
commit "Adiciona X"
sha=$(git -C "$REPO" rev-parse --short HEAD)
expect falha "commit sem sign-off falha e aponta o commit" "$sha"

new_repo
commit $'Adiciona X\n\nSigned-off-by: Bia Outra <bia@example.com>'
expect falha "sign-off de outra pessoa (e-mail diferente do autor e do committer) falha"

new_repo
commit $'Adiciona X\n\nSigned-off-by: Ana Autora <ANA@Example.COM>'
expect passa "e-mail do sign-off é comparado sem diferenciar maiúsculas"

new_repo
commit $'Adiciona X\n\nSigned-off-by: Ana Autora'
expect falha "Signed-off-by sem <e-mail> falha"

new_repo
commit $'Adiciona X\n\nSigned-off-by: Ana Autora <semarroba>'
expect falha "Signed-off-by com e-mail malformado (sem @) falha"

new_repo
commit $'Rebase\n\nSigned-off-by: Bia Outra <bia@example.com>' \
  "Bia Outra" "bia@example.com" "Ana Autora" "ana@example.com"
expect passa "sign-off do autor passa mesmo com outro committer (cherry-pick)"

new_repo
commit $'Rebase\n\nSigned-off-by: Ana Autora <ana@example.com>' \
  "Bia Outra" "bia@example.com" "Ana Autora" "ana@example.com"
expect passa "sign-off do committer passa mesmo com outro autor (quem aplicou o patch)"

new_repo
commit $'Adiciona X\n\nCo-Authored-By: Claude <noreply@anthropic.com>'
expect falha "Co-Authored-By não substitui o sign-off"

new_repo
commit $'Primeiro\n\nSigned-off-by: Ana Autora <ana@example.com>'
commit "Segundo, sem sign-off"
bad=$(git -C "$REPO" rev-parse --short HEAD)
expect falha "com dois commits, um sem sign-off, o PR falha" "$bad"

new_repo
commit $'Primeiro\n\nSigned-off-by: Ana Autora <ana@example.com>'
commit $'Segundo\n\nSigned-off-by: Ana Autora <ana@example.com>'
expect passa "todos os commits com sign-off passam"

new_repo
git -C "$REPO" switch -q -c lado
commit $'No lado\n\nSigned-off-by: Ana Autora <ana@example.com>'
git -C "$REPO" switch -q main
commit $'Na main\n\nSigned-off-by: Ana Autora <ana@example.com>'
git -C "$REPO" merge -q --no-ff lado -m "Merge sem sign-off"
expect passa "commit de merge sem sign-off é ignorado (os demais têm)"

new_repo
commit "Bump de dependência" "dependabot[bot]" "49699333+dependabot[bot]@users.noreply.github.com"
expect passa "autor dependabot[bot] sem sign-off é isento"

new_repo
expect passa "intervalo sem commits passa"

echo
echo "$pass passaram, $fail falharam"
[ "$fail" -eq 0 ]
