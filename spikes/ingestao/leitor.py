"""Leitor de ZIP de CSV em fluxo (spike descartável do ADR 0006).

Aplica as decisões 1, 5 e 6 do ADR 0005:
- lê pelo NOME da coluna do cabeçalho, nunca pela posição;
- devolve só as colunas da allowlist (o resto é descartado na leitura);
- coluna da allowlist ausente: falha fechada, antes de devolver qualquer linha do item;
- coluna nova fora da allowlist: ignorada e registrada em `colunas_ignoradas`;
- linha com número de colunas diferente do cabeçalho: rejeitada e contada;
- itens do ZIP que não são CSV (ex.: leiame.pdf) são ignorados.

A atomicidade da carga (nada gravado se um item falhar) é da transação de quem consome.
Codificação: ISO-8859-1, que nunca falha ao decodificar e preserva os bytes. Se a fonte
usar Windows-1252 (aspas tipográficas), isso precisa ser conferido antes de produção.
"""
import csv
import hashlib
import io
import zipfile


class ColunaAusente(Exception):
    """Coluna da allowlist ausente no cabeçalho de um item."""


class LeitorZip:
    def __init__(self, caminho, allowlist, *, delimitador=";", encoding="iso-8859-1"):
        self.caminho = caminho
        self.allowlist = list(allowlist)
        self.delimitador = delimitador
        self.encoding = encoding
        self.rejeitadas = 0
        self.colunas_ignoradas = set()

    def linhas(self):
        """Gera (nome_do_item, {coluna: valor}) só com as colunas da allowlist."""
        with zipfile.ZipFile(self.caminho) as zf:
            for info in zf.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".csv"):
                    continue
                with zf.open(info) as bruto:
                    texto = io.TextIOWrapper(bruto, encoding=self.encoding, newline="")
                    leitor = csv.reader(texto, delimiter=self.delimitador)
                    yield from self._item(info.filename, leitor)

    def _item(self, nome, leitor):
        cabecalho = next(leitor, None)
        if cabecalho is None:
            return
        cabecalho[0] = cabecalho[0].lstrip("﻿")
        posicao = {}
        for i, coluna in enumerate(cabecalho):
            posicao.setdefault(coluna, i)
        faltando = [c for c in self.allowlist if c not in posicao]
        if faltando:
            raise ColunaAusente(f"{nome}: faltam {faltando}")
        self.colunas_ignoradas |= set(cabecalho) - set(self.allowlist)
        indices = [(c, posicao[c]) for c in self.allowlist]
        largura = len(cabecalho)
        for linha in leitor:
            if not linha:
                continue
            if len(linha) != largura:
                self.rejeitadas += 1
                continue
            yield nome, {c: linha[i] for c, i in indices}


def sha256_arquivo(caminho, bloco=1024 * 1024):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        while pedaco := f.read(bloco):
            h.update(pedaco)
    return h.hexdigest()
