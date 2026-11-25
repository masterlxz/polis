from django.urls import re_path

from . import views

# O padrão só casa legislatura e id da Câmara de 1 a 9 dígitos (cabem no int32 do parser);
# qualquer outra coisa cai no 404 padrão, sem chegar ao banco.
# Sem zero à esquerda ([1-9][0-9]{0,8}): o int() o ignoraria e haveria duas URLs para um recurso.
# Nas rotas deste arquivo, [0-9] e não \d: o \d do Python casa dígitos de outras escritas
# (o int() os lê), que chegariam ao banco.
urlpatterns = [
    re_path(
        r"^deputados/(?P<legislature>[1-9][0-9]{0,8})-(?P<camara_id>[1-9][0-9]{0,8})/$",
        views.deputy_profile,
        name="deputy-profile",
    ),
    re_path(
        r"^deputados/(?P<legislature>[1-9][0-9]{0,7})-(?P<camara_id>[1-9][0-9]{0,8})/votos/$",
        views.deputy_votes,
        name="deputy-votes",
    ),
    # Código do Senado de 1 a 9 dígitos (cabe no int32 do parser); o resto é 404 sem banco.
    re_path(
        r"^senadores/(?P<senate_id>[1-9][0-9]{0,8})/$",
        views.senator_profile,
        name="senator-profile",
    ),
    re_path(
        r"^senadores/(?P<senate_id>[1-9][0-9]{0,8})/votos/$",
        views.senator_votes,
        name="senator-votes",
    ),
    re_path(r"^senado/votacoes/$", views.senate_voting_list, name="senate-voting-list"),
    # Código da votação de 1 a 9 dígitos, como o do senador; o resto é 404 sem banco.
    re_path(
        r"^senado/votacoes/(?P<code>[1-9][0-9]{0,8})/$",
        views.senate_voting_detail,
        name="senate-voting-detail",
    ),
    re_path(r"^camara/votacoes/$", views.camara_voting_list, name="camara-voting-list"),
    # O id da votação da Câmara é TEXTO (`2641546-7`) e a rota o casa como o parser da normalização
    # o grava (`[0-9]{1,10}-[0-9]{1,10}`, ASCII `[0-9]` e não `\d`): `01-2` e `1-2` são registros
    # distintos, então não há forma canônica a impor; recusar o zero à esquerda deixaria o dado na
    # lista sem URL de detalhe. Até 20 caracteres no total (o varchar(20) do banco), pelo
    # lookahead, sem `$` dentro dele: o `$` do `re` casa antes de um `\n` final. O resto é 404 sem
    # banco (ADR 0032).
    re_path(
        r"^camara/votacoes/(?=[0-9-]{3,20}/)(?P<voting_id>[0-9]{1,10}-[0-9]{1,10})/$",
        views.camara_voting_detail,
        name="camara-voting-detail",
    ),
]
