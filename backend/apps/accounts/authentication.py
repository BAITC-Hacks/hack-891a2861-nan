from django.core import signing
from rest_framework import authentication, exceptions

from .models import User

TOKEN_SALT = "career-quest-auth-v1"


def issue_token(user: User) -> str:
    return signing.dumps({"user_id": user.pk}, salt=TOKEN_SALT, compress=True)


class SignedTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode().split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != self.keyword.lower():
            raise exceptions.AuthenticationFailed("Invalid Authorization header")
        try:
            payload = signing.loads(header[1], salt=TOKEN_SALT, max_age=12 * 60 * 60)
            user = User.objects.get(pk=payload["user_id"], is_active=True)
        except (signing.BadSignature, signing.SignatureExpired, KeyError, User.DoesNotExist) as exc:
            raise exceptions.AuthenticationFailed("Invalid or expired token") from exc
        return user, header[1]
