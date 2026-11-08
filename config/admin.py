from django_otp.admin import OTPAdminSite


class PolisAdminSite(OTPAdminSite):
    """Admin que só aceita operador verificado por TOTP (ADR 0019).

    O `OTPAdminSite` nasce com o nome `otpadmin`, o que quebraria o namespace
    `admin:` usado pelas URLs e pelos templates; por isso o nome volta a `admin`.
    """

    def __init__(self, name="admin"):
        super().__init__(name)
