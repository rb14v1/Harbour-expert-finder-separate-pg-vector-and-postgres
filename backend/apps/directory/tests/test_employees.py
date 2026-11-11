from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.common.test_utils import auth_client, create_user
from apps.directory.models import Employee


def make_employee(**kwargs):
    defaults = {
        "full_name": "Test Person",
        "department": "Engineering",
        "title": "Engineer",
        "skills_summary": "Python",
        "bio": "Works on things.",
    }
    defaults.update(kwargs)
    return Employee.objects.create(**defaults)


class EmployeeListRetrieveTests(APITestCase):
    def setUp(self):
        self.employee_user = create_user(
            email="emp@example.com", role="employee", department="Engineering"
        )
        self.hr_user = create_user(email="hr@example.com", role="hr_admin", department="HR")
        self.profile = make_employee(full_name="Jamie Doe", user=self.employee_user)
        self.other_profile = make_employee(full_name="Other Person", department="Finance")

    def test_unauthenticated_request_rejected(self):
        response = APIClient().get(reverse("employee-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_any_authenticated_user_can_list_directory(self):
        client = auth_client(self.employee_user)
        response = client.get(reverse("employee-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(self.profile.id, ids)
        self.assertIn(self.other_profile.id, ids)

    def test_any_authenticated_user_can_retrieve_any_profile(self):
        client = auth_client(self.employee_user)
        response = client.get(reverse("employee-detail", args=[self.other_profile.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Other Person")


class EmployeeWritePermissionTests(APITestCase):
    def setUp(self):
        self.employee_user = create_user(
            email="emp@example.com", role="employee", department="Engineering"
        )
        self.other_employee_user = create_user(
            email="other@example.com", role="employee", department="Sales"
        )
        self.hr_user = create_user(email="hr@example.com", role="hr_admin", department="HR")
        self.profile = make_employee(full_name="Jamie Doe", user=self.employee_user)

    def test_employee_cannot_create_profile(self):
        client = auth_client(self.employee_user)
        response = client.post(
            reverse("employee-list"),
            {"full_name": "New Person", "department": "Sales"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_admin_can_create_profile(self):
        client = auth_client(self.hr_user)
        response = client.post(
            reverse("employee-list"),
            {"full_name": "New Person", "department": "Sales"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_employee_can_edit_own_profile(self):
        client = auth_client(self.employee_user)
        response = client.patch(
            reverse("employee-detail", args=[self.profile.id]),
            {"bio": "Updated bio."},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Updated bio.")

    def test_employee_cannot_edit_others_profile(self):
        other_profile = make_employee(full_name="Someone Else", user=self.other_employee_user)
        client = auth_client(self.employee_user)
        response = client.patch(
            reverse("employee-detail", args=[other_profile.id]),
            {"bio": "Hacked bio."},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        other_profile.refresh_from_db()
        self.assertNotEqual(other_profile.bio, "Hacked bio.")

    def test_hr_admin_can_edit_any_profile(self):
        client = auth_client(self.hr_user)
        response = client.patch(
            reverse("employee-detail", args=[self.profile.id]),
            {"title": "Staff Engineer"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_employee_cannot_delete_profile(self):
        client = auth_client(self.employee_user)
        response = client.delete(reverse("employee-detail", args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_admin_can_delete_profile(self):
        client = auth_client(self.hr_user)
        response = client.delete(reverse("employee-detail", args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Employee.objects.filter(id=self.profile.id).exists())

    def test_blank_full_name_rejected(self):
        client = auth_client(self.hr_user)
        response = client.post(
            reverse("employee-list"),
            {"full_name": "   ", "department": "Sales"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
