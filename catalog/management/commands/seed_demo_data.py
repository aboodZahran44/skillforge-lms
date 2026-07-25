from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from catalog.models import Course, Lesson, Section

User = get_user_model()

COURSES = [
    {
        "title": "Introduction to Python",
        "slug": "intro-to-python",
        "description": "A beginner-friendly tour of Python fundamentals.",
        "sections": [
            {
                "title": "Basics",
                "lessons": [
                    (
                        "Variables and types",
                        "Python variables don't require an explicit type declaration. "
                        "A name is bound to a value with a single equals sign, and the "
                        "interpreter infers the type from the value itself.",
                    ),
                    (
                        "Control flow",
                        "if, elif, and else statements let a program branch based on a "
                        "condition. Indentation, not curly braces, defines each block.",
                    ),
                ],
            },
            {
                "title": "Functions",
                "lessons": [
                    (
                        "Defining functions",
                        "Functions are defined with the def keyword, followed by a name "
                        "and a parameter list. A function that reaches its end without a "
                        "return statement implicitly returns None.",
                    ),
                ],
            },
        ],
    },
    {
        "title": "Workplace Safety Basics",
        "slug": "workplace-safety-basics",
        "description": "Core safety practices every employee should know.",
        "sections": [
            {
                "title": "Hazard awareness",
                "lessons": [
                    (
                        "Identifying common hazards",
                        "Workplace hazards fall into categories such as physical, "
                        "chemical, and ergonomic. Recognizing the category helps "
                        "determine the right control measure.",
                    ),
                ],
            },
        ],
    },
    {
        "title": "Effective Communication at Work",
        "slug": "effective-communication",
        "description": "Practical techniques for clearer workplace communication.",
        "sections": [
            {
                "title": "Foundations",
                "lessons": [
                    (
                        "Active listening",
                        "Active listening means fully concentrating on the speaker "
                        "rather than preparing a response while they're still talking. "
                        "Paraphrasing what you heard confirms understanding.",
                    ),
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed demo courses, sections, and lessons for local development."

    def handle(self, *args, **options):
        instructor, created = User.objects.get_or_create(
            email="instructor@skillforge.local",
            defaults={"full_name": "Demo Instructor"},
        )
        if created:
            instructor.set_password("demopass123")
            instructor.save()
            self.stdout.write(self.style.SUCCESS(f"Created instructor: {instructor.email}"))

        for course_data in COURSES:
            course, _ = Course.objects.get_or_create(
                slug=course_data["slug"],
                defaults={
                    "title": course_data["title"],
                    "description": course_data["description"],
                    "instructor": instructor,
                    "status": Course.Status.PUBLISHED,
                },
            )

            for section_order, section_data in enumerate(course_data["sections"], start=1):
                section, _ = Section.objects.get_or_create(
                    course=course,
                    order=section_order,
                    defaults={"title": section_data["title"]},
                )

                for lesson_order, (title, content) in enumerate(section_data["lessons"], start=1):
                    Lesson.objects.get_or_create(
                        section=section,
                        order=lesson_order,
                        defaults={"title": title, "content": content},
                    )

            self.stdout.write(self.style.SUCCESS(f"Seeded: {course.title}"))

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))