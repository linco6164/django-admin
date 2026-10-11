"""Compile project PO catalogs on systems without GNU gettext installed."""
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Compile project locale/**/*.po to .mo using polib (no msgfmt required).'

    def handle(self, *args, **options):
        count = 0
        for locale_root in settings.LOCALE_PATHS:
            for path in sorted(Path(locale_root).glob('*/LC_MESSAGES/*.po')):
                catalog = polib.pofile(str(path), encoding='utf-8', check_for_duplicates=True)
                empty = [entry.msgid for entry in catalog if not entry.obsolete and not entry.translated()]
                if empty:
                    raise CommandError(f'{path}: {len(empty)} untranslated or fuzzy entries.')
                target = path.with_suffix('.mo')
                catalog.save_as_mofile(str(target))
                self.stdout.write(f'{target.relative_to(settings.BASE_DIR)}: {len(catalog)} entries')
                count += 1
        if not count:
            raise CommandError('No project PO catalogs found.')
        self.stdout.write(self.style.SUCCESS(f'Compiled {count} catalog(s).'))
