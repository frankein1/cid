# core/tests/test_models.py

from django.test import TestCase
from core.models import User, Service, Profil


class UserModelTest(TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            code='TEST',
            nom='Service Test'
        )
    
    def test_create_user(self):
        """Test création utilisateur"""
        user = User.objects.create_user(
            username='test',
            email='test@cd13.fr',
            password='test123',
            matricule='12345',
            service_principal=self.service
        )
        self.assertEqual(user.username, 'test')
        self.assertTrue(user.check_password('test123'))
    
    def test_user_profil(self):
        """Test assignation profil"""
        profil = Profil.objects.create(
            code='TEST',
            nom='Test Profil'
        )
        user = User.objects.create_user(
            username='test2',
            matricule='12346',
            service_principal=self.service
        )
        user.profils.add(profil)
        self.assertTrue(user.a_profil('TEST'))
