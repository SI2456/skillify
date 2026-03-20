from django.core.management.base import BaseCommand
from core.models import Skill


class Command(BaseCommand):
    help = 'Create default skills (run this if skills are missing)'

    def handle(self, *args, **kwargs):
        skill_data = [
            ('Dance', 'bi-music-note-beamed'),
            ('Python', 'bi-code-slash'),
            ('Guitar', 'bi-music-note'),
            ('Photography', 'bi-camera'),
            ('Public Speaking', 'bi-mic'),
            ('UI Design', 'bi-palette'),
            ('Data Science', 'bi-graph-up'),
            ('Singing', 'bi-soundwave'),
            ('Video Editing', 'bi-film'),
            ('Marketing', 'bi-megaphone'),
        ]

        created_count = 0
        for name, icon in skill_data:
            _, created = Skill.objects.get_or_create(name=name, defaults={'icon': icon})
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done! {created_count} new skills created. {len(skill_data) - created_count} already existed.'
        ))
