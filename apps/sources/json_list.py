"""Esqueleto (sem lógica) do leitor de listas JSON paginadas; a lógica vem depois dos testes."""

MAX_PAGES = 20


class JsonListError(Exception):
    """Base dos erros de formato da lista JSON."""


class InvalidJsonError(JsonListError):
    pass


class MissingFieldError(JsonListError):
    pass


class DuplicateItemError(JsonListError):
    pass


class TooManyPagesError(JsonListError):
    pass


def fetch_pages(client, url, destination, *, page_size=100, max_pages=None, unique_field="id"):
    raise NotImplementedError


class JsonListReader:
    def __init__(self, path, allowed_columns):
        raise NotImplementedError
