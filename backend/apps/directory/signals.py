"""
Keeps the "employees" Qdrant collection in sync with Employee rows.

On save: scheduled via transaction.on_commit so a vector is never written
for a Postgres write that later rolls back (e.g. a failed request inside an
atomic block) - see apps/common/qdrant_store.py module docstring for why
this two-database split needs explicit sync code at all.

On delete: no rollback risk, so the Qdrant point is removed directly in the
post_delete handler.
"""
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common import qdrant_store
from apps.common.ai import get_embedding
from apps.directory.models import Employee


def sync_employee_to_qdrant(employee_id: int) -> None:
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return
    text = f"{employee.skills_summary} {employee.bio}".strip() or employee.full_name
    vector = get_embedding(text)
    qdrant_store.upsert_point(
        qdrant_store.EMPLOYEE_COLLECTION,
        employee.id,
        vector,
        {"department": employee.department},
    )


@receiver(post_save, sender=Employee)
def employee_saved(sender, instance, **kwargs):
    transaction.on_commit(lambda: sync_employee_to_qdrant(instance.id))


@receiver(post_delete, sender=Employee)
def employee_deleted(sender, instance, **kwargs):
    qdrant_store.delete_point(qdrant_store.EMPLOYEE_COLLECTION, instance.id)
