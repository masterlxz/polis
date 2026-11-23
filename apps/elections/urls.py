from django.urls import re_path

from . import views

# O padrão só casa ciclo de 4 dígitos e SQ_CANDIDATO de 1 a 12 (cabe no PositiveBigIntegerField);
# qualquer outra coisa cai no 404 padrão, sem chegar ao banco.
urlpatterns = [
    re_path(r"^busca/$", views.person_search, name="person-search"),
    re_path(
        # [0-9] e não \d: o \d do Python casa dígitos de outras escritas, que chegariam ao banco.
        r"^pessoas/(?P<cycle>[0-9]{4})-(?P<candidate_id>[0-9]{1,12})/$",
        views.person_profile,
        name="person-profile",
    ),
]
