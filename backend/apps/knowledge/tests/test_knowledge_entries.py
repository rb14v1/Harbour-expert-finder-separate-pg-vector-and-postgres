from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.common.test_utils import auth_client, create_user
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry


class KnowledgeEntryCreatePermissionTests(APITestCase):
    def setUp(self):
        self.employee_user = create_user(
            email="emp@example.com", role="employee", department="Engineering"
        )
        self.hr_user = create_user(email="hr@example.com", role="hr_admin", department="HR")
        self.employee_profile = Employee.objects.create(
            full_name="Emp Person", department="Engineering", user=self.employee_user
        )
        self.hr_profile = Employee.objects.create(
            full_name="HR Person", department="HR", user=self.hr_user
        )

    def test_employee_can_create_public_qna_entry(self):
        client = auth_client(self.employee_user)
        response = client.post(
            reverse("knowledgeentry-list"),
            {"title": "How do I do X?", "body": "Do Y.", "entry_type": "qna"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        entry = KnowledgeEntry.objects.get(id=response.data["id"])
        self.assertEqual(entry.author, self.employee_profile)
        self.assertEqual(entry.visibility_departments, [])

    def test_employee_cannot_create_policy_entry(self):
        client = auth_client(self.employee_user)
        response = client.post(
            reverse("knowledgeentry-list"),
            {"title": "A policy", "body": "Rules.", "entry_type": "policy"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_cannot_create_restricted_entry(self):
        client = auth_client(self.employee_user)
        response = client.post(
            reverse("knowledgeentry-list"),
            {
                "title": "Restricted qna",
                "body": "Secret.",
                "entry_type": "qna",
                "visibility_departments": ["Finance"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hr_admin_can_create_restricted_policy_entry(self):
        client = auth_client(self.hr_user)
        response = client.post(
            reverse("knowledgeentry-list"),
            {
                "title": "Restricted policy",
                "body": "Sensitive.",
                "entry_type": "policy",
                "visibility_departments": ["Engineering"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        entry = KnowledgeEntry.objects.get(id=response.data["id"])
        self.assertEqual(entry.visibility_departments, ["Engineering"])

    def test_create_without_employee_profile_rejected(self):
        bare_user = create_user(email="bare@example.com", role="employee", department="Sales")
        client = auth_client(bare_user)
        response = client.post(
            reverse("knowledgeentry-list"),
            {"title": "No profile", "body": "Body.", "entry_type": "qna"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_request_rejected(self):
        response = APIClient().get(reverse("knowledgeentry-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blank_title_rejected(self):
        client = auth_client(self.employee_user)
        response = client.post(
            reverse("knowledgeentry-list"),
            {"title": "   ", "body": "Body.", "entry_type": "qna"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class KnowledgeEntryWritePermissionTests(APITestCase):
    def setUp(self):
        self.employee_user = create_user(
            email="emp@example.com", role="employee", department="Engineering"
        )
        self.other_employee_user = create_user(
            email="other@example.com", role="employee", department="Engineering"
        )
        self.hr_user = create_user(email="hr@example.com", role="hr_admin", department="HR")

        self.employee_profile = Employee.objects.create(
            full_name="Emp Person", department="Engineering", user=self.employee_user
        )
        self.other_profile = Employee.objects.create(
            full_name="Other Person", department="Engineering", user=self.other_employee_user
        )

        self.own_entry = KnowledgeEntry.objects.create(
            title="Own entry", body="Body", entry_type="qna", author=self.employee_profile
        )
        self.others_entry = KnowledgeEntry.objects.create(
            title="Others entry", body="Body", entry_type="qna", author=self.other_profile
        )

    def test_author_can_edit_own_entry(self):
        client = auth_client(self.employee_user)
        response = client.patch(
            reverse("knowledgeentry-detail", args=[self.own_entry.id]), {"body": "Updated body"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.own_entry.refresh_from_db()
        self.assertEqual(self.own_entry.body, "Updated body")

    def test_non_author_cannot_edit_entry(self):
        client = auth_client(self.employee_user)
        response = client.patch(
            reverse("knowledgeentry-detail", args=[self.others_entry.id]), {"body": "Hacked"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.others_entry.refresh_from_db()
        self.assertNotEqual(self.others_entry.body, "Hacked")

    def test_hr_admin_can_edit_any_entry(self):
        client = auth_client(self.hr_user)
        response = client.patch(
            reverse("knowledgeentry-detail", args=[self.others_entry.id]), {"body": "HR edit"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_author_can_delete_own_entry(self):
        client = auth_client(self.employee_user)
        response = client.delete(reverse("knowledgeentry-detail", args=[self.own_entry.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(KnowledgeEntry.objects.filter(id=self.own_entry.id).exists())

    def test_non_author_cannot_delete_entry(self):
        client = auth_client(self.employee_user)
        response = client.delete(reverse("knowledgeentry-detail", args=[self.others_entry.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(KnowledgeEntry.objects.filter(id=self.others_entry.id).exists())

    def test_hr_admin_can_delete_any_entry(self):
        client = auth_client(self.hr_user)
        response = client.delete(reverse("knowledgeentry-detail", args=[self.own_entry.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
