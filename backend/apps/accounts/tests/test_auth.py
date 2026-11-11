from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.test_utils import auth_client, create_user


class LoginAndMeTests(APITestCase):
    def setUp(self):
        self.user = create_user(
            email="u1@example.com",
            password="StrongPass123!",
            full_name="U One",
            role="employee",
            department="Engineering",
        )

    def test_login_returns_tokens(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "u1@example.com", "password": "StrongPass123!"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_wrong_password(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "u1@example.com", "password": "WrongPass!"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint(self):
        client = auth_client(self.user)
        response = client.get(reverse("user-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "u1@example.com")
        self.assertEqual(response.data["role"], "employee")
        self.assertEqual(response.data["department"], "Engineering")

    def test_me_requires_authentication(self):
        from rest_framework.test import APIClient

        response = APIClient().get(reverse("user-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(reverse("auth-login"), {"email": "u1@example.com", "password": "StrongPass123!"})
        refresh = login_response.data["refresh"]
        client = auth_client(self.user)
        logout_response = client.post(reverse("auth-logout"), {"refresh": refresh})
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post(reverse("auth-refresh"), {"refresh": refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotates_token(self):
        login_response = self.client.post(reverse("auth-login"), {"email": "u1@example.com", "password": "StrongPass123!"})
        old_refresh = login_response.data["refresh"]

        refresh_response = self.client.post(reverse("auth-refresh"), {"refresh": old_refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)
        self.assertIn("refresh", refresh_response.data)
        self.assertNotEqual(refresh_response.data["refresh"], old_refresh)

        # Old refresh token was rotated out and blacklisted - reusing it
        # must now fail.
        reuse_response = self.client.post(reverse("auth-refresh"), {"refresh": old_refresh})
        self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)
