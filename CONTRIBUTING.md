# Como contribuir

O código do polis é licenciado sob AGPL-3.0 (ADR 0002). Contribuições de código seguem o **DCO** (*Developer Certificate of Origin*, ADR 0004): cada commit precisa de uma linha `Signed-off-by` com o seu nome e e-mail, declarando que você tem o direito de enviar aquele código sob a licença do projeto. O texto do DCO está em <https://developercertificate.org/>.

Você continua dono do copyright do que enviar. Em contrapartida, o projeto não pode relicenciar o código sem o consentimento de todos os contribuidores.

## Como assinar

```bash
git commit -s -m "Mensagem do commit"
```

O `-s` acrescenta ao fim da mensagem:

```
Signed-off-by: Seu Nome <seu@email.com>
```

O e-mail precisa ser o do **autor** ou o do **committer** do commit.

## Esqueci de assinar

```bash
# último commit
git commit --amend -s --no-edit

# todos os commits da branch em relação à main
git rebase --signoff main
git push --force-with-lease
```

## O que o CI confere

O check `dco` roda em todo PR (inclusive nos do mantenedor) e falha se algum commit do PR, fora merge commits, não tiver o `Signed-off-by` acima. O autor `dependabot[bot]` é isento.

Prefira mesclar com **merge commit** (não squash): no squash, o `Signed-off-by` só sobrevive se estiver na mensagem final.
