from tests.utils.authentication import admin_required

@admin_required("api/mail/send-mail/", "post")
def test_mail_admin_required(client):
    pass
