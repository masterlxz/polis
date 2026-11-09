from django.urls import re_path

from . import views

# O padrão só casa ciclo de 4 dígitos e SQ_CANDIDATO de 1 a 12 (cabe no PositiveBigIntegerField);
# qualquer outra coisa cai no 404 padrão, sem chegar ao banco.
urlpatterns = [
    re_path(r"^busca/$", views.person_search, name="person-search"),
    re_path(
        r"^pessoas/(?P<cycle>\d{4})-(?P<candidate_id>\d{1,12})/$",
        views.person_profile,
        name="person-profile",
    ),
]
