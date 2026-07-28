import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import qrcode
from io import BytesIO
from flask import current_app

def generate_approval_pdf(event, approvals):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    Story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))

    # Header
    Story.append(Paragraph("Enterprise College Event Management", styles['Title']))
    Story.append(Spacer(1, 12))
    Story.append(Paragraph("Certificate of Approval", styles['Title']))
    Story.append(Spacer(1, 12))

    # Event Details
    Story.append(Paragraph(f"<b>Event ID:</b> {event.event_id}", styles['Normal']))
    Story.append(Paragraph(f"<b>Title:</b> {event.title}", styles['Normal']))
    Story.append(Paragraph(f"<b>Type:</b> {event.event_type}", styles['Normal']))
    Story.append(Paragraph(f"<b>Organizer:</b> {event.organizer_name}", styles['Normal']))
    Story.append(Paragraph(f"<b>Date:</b> {event.event_date} <b>Time:</b> {event.event_time}", styles['Normal']))
    Story.append(Paragraph(f"<b>Venue:</b> {event.venue}", styles['Normal']))
    Story.append(Paragraph(f"<b>Budget:</b> ${event.budget}", styles['Normal']))
    Story.append(Paragraph(f"<b>Status:</b> {event.status}", styles['Normal']))
    Story.append(Spacer(1, 12))

    # Approval Timeline Table
    Story.append(Paragraph("Approval Timeline", styles['Heading2']))
    Story.append(Spacer(1, 6))

    data = [['Role', 'Status', 'Date', 'Comments']]
    for app in approvals:
        date_str = app.action_date.strftime('%Y-%m-%d %H:%M') if app.action_date else '-'
        data.append([
            app.required_role,
            app.status,
            date_str,
            Paragraph(app.comments or '', styles['Normal'])
        ])

    t = Table(data, colWidths=[80, 80, 100, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    Story.append(t)
    Story.append(Spacer(1, 24))

    # QR Code
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    from flask import url_for
    try:
        verify_url = url_for('events.view', event_id=event.id, _external=True)
    except RuntimeError:
        verify_url = f"http://127.0.0.1:5000/events/{event.id}"
        
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = BytesIO()
    img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    
    Story.append(Paragraph("Verification QR Code:", styles['Heading3']))
    Story.append(Spacer(1, 6))
    Story.append(Image(qr_buffer, width=100, height=100, hAlign='LEFT'))

    # Build PDF
    doc.build(Story)
    pdf_out = buffer.getvalue()
    buffer.close()
    return pdf_out
