"""Leitor de ZIP de CSV (spike descartável do ADR 0006).

v0 (ingênua): lê pelo nome da coluna, decodifica ISO-8859-1 e transmite em fluxo,
mas NÃO aplica a allowlist, NÃO falha fechada, NÃO rejeita linha com número de
colunas errado e NÃO ignora itens que não são CSV. Existe só para provar que os
testes distinguem uma leitura ingênua de uma leitura que segue o ADR 0005.
"""
import csv
import hashlib
import io
import zipfile


class ColunaAusente(Exception):
    """Coluna da allowlist ausente no cabeçalho de um item."""


class LeitorZip:
    def __init__(self, caminho, allowlist):
        self.caminho = caminho
        self.allowlist = list(allowlist)
        self.rejeitadas = 0
        self.colunas_ignoradas = set()

    def linhas(self):
        with zipfile.ZipFile(self.caminho) as zf:
            for info in zf.infolist():
                with zf.open(info) as bruto:
                    texto = io.TextIOWrapper(bruto, encoding="iso-8859-1", newline="")
                    for linha in csv.DictReader(texto, delimiter=";"):
                        yield info.filename, dict(linha)


def sha256_arquivo(caminho, bloco=1024 * 1024):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        while pedaco := f.read(bloco):
            h.update(pedaco)
    return h.hexdigest()
