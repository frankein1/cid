# core/views/gubed.py
import time
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from core.models import Service, Profil


User = get_user_model()


def trigger_test_user(request):
    """
    Vue de debug accessible à une URL secrète.
    """
    if not request.user.is_superuser:
        return HttpResponse("Forbidden", status=403)

    service, _ = Service.objects.get_or_create(
        code='TEST',
        defaults={'nom': 'Service Test'}
    )
    profil, _ = Profil.objects.get_or_create(
        code='TEST',
        defaults={'nom': 'Test Profil'},
    )

    user = User.objects.create_user(
        username='debug_test',
        email='debug_test@cd13.fr',
        password='test123',
        matricule='123456',
        service_principal=service,
    )
    user.profils.add(profil)

    print("OK")

    time.sleep(15)
    User.objects.filter(username='debug_test').delete()

    return HttpResponse("OK")