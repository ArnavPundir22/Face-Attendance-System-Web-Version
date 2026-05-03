"""
Email utility functions.

Covers:
  - Password-reset OTP emails
  - Attendance PDF generation and email delivery
"""

import smtplib
from datetime import datetime
from email.message import EmailMessage
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config


def _smtp_connection():
    """Return an authenticated Gmail SMTP-SSL connection."""
    smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp.login(config.EMAIL_USER, config.EMAIL_PASS)
    return smtp


def send_password_reset_otp(recipient_email: str, otp: str, username: str) -> None:
    """Send a password-reset OTP to *recipient_email*."""
    msg = EmailMessage()
    msg['Subject'] = '🔐 Password Reset OTP – Face Attendance System'
    msg['From'] = config.EMAIL_USER
    msg['To'] = recipient_email
    msg.set_content(
        f"Hello {username},\n\n"
        f"Your password reset OTP is: {otp}\n\n"
        f"This code is valid for {config.OTP_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request a password reset, please ignore this email.\n\n"
        f"— Face Attendance System"
    )
    with _smtp_connection() as smtp:
        smtp.send_message(msg)


def build_attendance_pdf(table_data: list) -> bytes:
    """Return a PDF (bytes) containing an attendance table.

    *table_data* is a list of rows (each row is a list/tuple of cell values).
    The column header row is prepended automatically.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Attendance Report", styles['Title']),
        Paragraph(
            datetime.now().strftime("Generated on %d %B %Y, %I:%M %p"),
            styles['Heading2'],
        ),
        Spacer(1, 12),
    ]

    headers = ['ID', 'Name', 'Program', 'Branch', 'Mobile', 'Status', 'Timestamp', 'Lecture', 'Section']
    table = Table([headers] + table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 10),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ]))
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()


def send_attendance_email(recipient_email: str, table_data: list) -> None:
    """Build and email a PDF attendance report to *recipient_email*.

    Raises ``smtplib.SMTPException`` (or subclass) on delivery failure.
    """
    pdf_data = build_attendance_pdf(table_data)

    msg = EmailMessage()
    msg['Subject'] = 'Attendance Report'
    msg['From'] = config.EMAIL_USER
    msg['To'] = recipient_email
    msg.set_content('Please find the attendance report attached.')
    msg.add_attachment(
        pdf_data,
        maintype='application',
        subtype='pdf',
        filename='attendance_report.pdf',
    )

    with _smtp_connection() as smtp:
        smtp.send_message(msg)
