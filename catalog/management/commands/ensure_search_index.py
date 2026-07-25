from django.core.management.base import BaseCommand
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from catalog import search


class Command(BaseCommand):
    help = "Create the Elasticsearch course index if it does not exist."

    def handle(self, *args, **options):
        try:
            search.ensure_index()
        except ESConnectionError:
            self.stderr.write(
                self.style.WARNING(
                    "Elasticsearch is unreachable; index not created. "
                    "Search will run in degraded (database) mode."
                )
            )
            return
        self.stdout.write(self.style.SUCCESS(f"Index '{search.INDEX_NAME}' is ready."))
