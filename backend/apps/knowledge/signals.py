"""
Keeps the "knowledge_entries" Qdrant collection in sync with KnowledgeEntry
rows - same on_commit / post_delete pattern as apps/directory/signals.py,
see that module's docstring for why.
"""
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common import qdrant_store
from apps.common.ai import get_embedding
from apps.knowledge.models import KnowledgeEntry


def sync_knowledge_entry_to_qdrant(entry_id: int) -> None:
    try:
        entry = KnowledgeEntry.objects.get(id=entry_id)
    except KnowledgeEntry.DoesNotExist:
        return
    text = f"{entry.title} {entry.body}"
    vector = get_embedding(text)
    qdrant_store.upsert_point(
        qdrant_store.KNOWLEDGE_COLLECTION,
        entry.id,
        vector,
        {
            "visibility_departments": entry.visibility_departments or [],
            "entry_type": entry.entry_type,
            "author_id": entry.author_id,
        },
    )


@receiver(post_save, sender=KnowledgeEntry)
def knowledge_entry_saved(sender, instance, **kwargs):
    transaction.on_commit(lambda: sync_knowledge_entry_to_qdrant(instance.id))


@receiver(post_delete, sender=KnowledgeEntry)
def knowledge_entry_deleted(sender, instance, **kwargs):
    qdrant_store.delete_point(qdrant_store.KNOWLEDGE_COLLECTION, instance.id)
