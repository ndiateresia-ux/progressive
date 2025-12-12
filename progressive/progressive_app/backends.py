from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from typing import Optional

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that uses email instead of username.
    Compatible with a custom User model where USERNAME_FIELD = 'email'.
    """

    def authenticate(
        self,
        request,
        email: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> Optional[User]:
        if not email or not password:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
