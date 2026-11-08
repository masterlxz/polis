from django.contrib.admin.apps import AdminConfig


class PolisAdminConfig(AdminConfig):
    default_site = "config.admin.PolisAdminSite"
