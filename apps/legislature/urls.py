from django.urls import re_path

from . import views

# O padrão só casa legislatura e id da Câmara de 1 a 9 dígitos (cabem no int32 do parser);
# qualquer outra coisa cai no 404 padrão, sem chegar ao banco.
urlpatterns = [
    re_path(
        r"^deputados/(?P<legislature>\d{1,9})-(?P<camara_id>\d{1,9})/$",
        views.deputy_profile,
        name="deputy-profile",
    ),
]
