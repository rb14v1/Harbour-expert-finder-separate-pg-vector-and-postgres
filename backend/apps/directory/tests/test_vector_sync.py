from django.test import TestCase

from apps.common import qdrant_store
from apps.directory.models import Employee


class EmployeeVectorSyncTests(TestCase):
    """Verifies the post_save/post_delete signals in apps/directory/signals.py
    actually land (and remove) points in the "employees" Qdrant collection.

    Django's TestCase wraps each test in an outer atomic transaction that is
    rolled back, not committed - transaction.on_commit() callbacks are never
    run in that case. captureOnCommitCallbacks(execute=True) manually runs
    any callbacks queued during the `with` block, which is the standard way
    to exercise on_commit-scheduled code under TestCase."""

    def test_save_upserts_point_into_employees_collection(self):
        with self.captureOnCommitCallbacks(execute=True):
            employee = Employee.objects.create(
                full_name="Sync Test Person",
                department="Engineering",
                title="QA Engineer",
                skills_summary="Automated testing, Selenium, pytest",
                bio="Loves finding bugs.",
            )

        point = qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, employee.id)
        self.assertIsNotNone(point)
        self.assertEqual(point.payload["department"], "Engineering")
        self.assertEqual(len(point.vector), 1536)

    def test_update_re_syncs_point(self):
        with self.captureOnCommitCallbacks(execute=True):
            employee = Employee.objects.create(
                full_name="Sync Update Person",
                department="Finance",
                skills_summary="Accounting",
                bio="",
            )

        with self.captureOnCommitCallbacks(execute=True):
            employee.department = "Sales"
            employee.save()

        point = qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, employee.id)
        self.assertIsNotNone(point)
        self.assertEqual(point.payload["department"], "Sales")

    def test_delete_removes_point(self):
        with self.captureOnCommitCallbacks(execute=True):
            employee = Employee.objects.create(
                full_name="Sync Delete Person",
                department="HR",
                skills_summary="Recruiting",
                bio="",
            )
        employee_id = employee.id
        self.assertIsNotNone(qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, employee_id))

        employee.delete()

        self.assertIsNone(qdrant_store.get_point(qdrant_store.EMPLOYEE_COLLECTION, employee_id))
