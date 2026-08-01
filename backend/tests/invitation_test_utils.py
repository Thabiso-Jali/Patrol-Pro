from contextlib import contextmanager

from backend.app.api.api_v1.endpoints import invitations


@contextmanager
def development_invitation_token_exposure():
    settings = invitations.settings
    previous_environment = settings.APP_ENV
    previous_exposure = settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS
    settings.APP_ENV = 'development'
    settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS = True
    try:
        yield
    finally:
        settings.APP_ENV = previous_environment
        settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS = previous_exposure


def post_development_invitation(client, *, headers, json):
    with development_invitation_token_exposure():
        return client.post('/api/v1/invitations', headers=headers, json=json)
