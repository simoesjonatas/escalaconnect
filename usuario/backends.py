from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class CustomBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        try:
            # busca o usuario por nome de usuario ou e-mail
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
            # user = User.objects.get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Mais de um usuário com o mesmo e-mail: deixa o ModelBackend tentar
            # pelo nome de usuário exato em vez de estourar erro 500.
            return None
