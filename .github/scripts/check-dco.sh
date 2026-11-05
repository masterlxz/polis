#!/usr/bin/env bash
# Exige DCO (ADR 0004): todo commit em <base>..<head> precisa de uma linha
# `Signed-off-by: Nome <email>` cujo e-mail seja o do autor ou o do committer
# (sem diferenciar maiúsculas). Merge commits e o autor dependabot[bot] são ignorados.
# Uso: check-dco.sh <base> <head>
set -u

if [ "$#" -ne 2 ]; then
  echo "uso: $0 <base> <head>" >&2
  exit 2
fi
base="$1"
head="$2"

bad=0
# --no-merges ignora merge commits; %x1f separa campos e %x1e termina cada commit.
while IFS=$'\x1f' read -r -d $'\x1e' sha author_name author_email committer_email body; do
  sha=${sha//$'\n'/}
  [ -z "$sha" ] && continue
  short=${sha:0:7}

  if [ "$author_name" = "dependabot[bot]" ]; then
    continue
  fi

  ok=0
  while IFS= read -r line; do
    if [[ "$line" =~ ^Signed-off-by:[[:space:]]+.+[[:space:]]\<([^<>[:space:]]+@[^<>[:space:]]+)\>[[:space:]]*$ ]]; then
      signer="${BASH_REMATCH[1],,}"
      if [ "$signer" = "${author_email,,}" ] || [ "$signer" = "${committer_email,,}" ]; then
        ok=1
        break
      fi
    fi
  done <<<"$body"

  if [ "$ok" -eq 0 ]; then
    echo "::error::Commit $short sem 'Signed-off-by: Nome <email>' do autor ou do committer (use git commit -s)."
    bad=1
  fi
done < <(git log --no-merges --format='%H%x1f%an%x1f%ae%x1f%ce%x1f%B%x1e' "$base..$head")

exit "$bad"
