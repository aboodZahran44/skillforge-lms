import io

from celery import shared_task
from django.apps import apps
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


@shared_task
def generate_certificate_pdf(attempt_id):
    QuizAttempt = apps.get_model("learning", "QuizAttempt")
    Certificate = apps.get_model("learning", "Certificate")

    attempt = QuizAttempt.objects.select_related("enrollment__user", "quiz__course").get(
        id=attempt_id
    )

    if not attempt.passed:
        return None

    existing = Certificate.objects.filter(attempt=attempt).first()
    if existing is not None:
        return existing.id

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(297, 700, "Certificate of Completion")

    pdf.setFont("Helvetica", 14)
    student_name = attempt.enrollment.user.full_name or attempt.enrollment.user.email
    pdf.drawCentredString(297, 640, f"Awarded to {student_name}")
    pdf.drawCentredString(297, 610, f"for completing {attempt.quiz.course.title}")
    pdf.drawCentredString(297, 580, f"Score: {attempt.score_percent}%")

    pdf.showPage()
    pdf.save()

    certificate = Certificate(attempt=attempt)
    certificate.pdf.save(
        f"certificate-attempt-{attempt.id}.pdf", ContentFile(buffer.getvalue()), save=True
    )
    return certificate.id
