"""
Verifies the data migration in apps/knowledge/migrations/0002_seed_demo_data.py.

By the time Django's test runner builds the test database it has already run
every migration (including this data migration), so the seeded rows are
simply present when these tests run - no need to invoke the migration
manually. (The migration module's name starts with a digit so it isn't
importable as `apps.knowledge.migrations.0002_...`; expected values are
duplicated here instead of imported.)
"""
from django.test import TestCase

from apps.accounts.models import User
from apps.common import qdrant_store
from apps.directory.models import Employee
from apps.knowledge.models import KnowledgeEntry

EMPLOYEE_EMAIL = "employee@example.com"
HR_ADMIN_EMAIL = "hradmin@example.com"
DEMO_PASSWORD = "demo12345"

EXPECTED_EMPLOYEE_COUNT = 10
EXPECTED_KNOWLEDGE_ENTRY_COUNT = 18
EXPECTED_DEPARTMENTS = {"Engineering", "HR", "Finance", "Sales"}


class SeedMigrationTests(TestCase):
    def test_demo_users_created_with_correct_roles(self):
        employee = User.objects.get(email=EMPLOYEE_EMAIL)
        self.assertTrue(employee.check_password(DEMO_PASSWORD))
        self.assertEqual(employee.role, "employee")
        self.assertEqual(employee.department, "Engineering")

        hr_admin = User.objects.get(email=HR_ADMIN_EMAIL)
        self.assertTrue(hr_admin.check_password(DEMO_PASSWORD))
        self.assertEqual(hr_admin.role, "hr_admin")
        self.assertEqual(hr_admin.department, "HR")

    def test_demo_users_have_linked_employee_profiles(self):
        employee = User.objects.get(email=EMPLOYEE_EMAIL)
        hr_admin = User.objects.get(email=HR_ADMIN_EMAIL)
        self.assertTrue(Employee.objects.filter(user=employee).exists())
        self.assertTrue(Employee.objects.filter(user=hr_admin).exists())

    def test_seed_employee_count_and_department_spread(self):
        self.assertEqual(Employee.objects.count(), EXPECTED_EMPLOYEE_COUNT)
        departments = set(Employee.objects.values_list("department", flat=True))
        self.assertTrue(EXPECTED_DEPARTMENTS.issubset(departments))

    def test_seed_knowledge_entry_count(self):
        self.assertEqual(KnowledgeEntry.objects.count(), EXPECTED_KNOWLEDGE_ENTRY_COUNT)

    def test_seed_includes_both_entry_types(self):
        types = set(KnowledgeEntry.objects.values_list("entry_type", flat=True))
        self.assertEqual(types, {"policy", "qna"})

    def test_seed_includes_department_restricted_entries(self):
        restricted = [e for e in KnowledgeEntry.objects.all() if e.visibility_departments]
        self.assertGreaterEqual(len(restricted), 3)

    def test_seed_includes_public_entries(self):
        public = [e for e in KnowledgeEntry.objects.all() if not e.visibility_departments]
        self.assertGreater(len(public), 0)

    def test_seed_employees_synced_to_qdrant(self):
        for employee in Employee.objects.all():
            point = qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, employee.id)
            self.assertIsNotNone(point, f"Employee {employee.id} missing from Qdrant")
            self.assertEqual(point.payload["department"], employee.department)

    def test_seed_knowledge_entries_synced_to_qdrant(self):
        for entry in KnowledgeEntry.objects.all():
            point = qdrant_store.get_point(qdrant_store.KNOWLEDGE_COLLECTION, entry.id)
            self.assertIsNotNone(point, f"KnowledgeEntry {entry.id} missing from Qdrant")
            self.assertEqual(point.payload["entry_type"], entry.entry_type)
