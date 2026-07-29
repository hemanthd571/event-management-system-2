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
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'gmu_logo.png')
    if os.path.exists(logo_path):
        Story.append(Image(logo_path, width=80, height=80))
        Story.append(Spacer(1, 12))
        
    Story.append(Paragraph("GM University Event Management", styles['Title']))
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
    Story.append(Paragraph(f"<b>Budget:</b> Rs. {event.budget}", styles['Normal']))
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
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#5C2C16')), # Betel Nut Brown
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FDF8ED')), # Very Light Gold
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E3B559')) # GMU Gold borders
    ]))
    Story.append(t)
    Story.append(Spacer(1, 24))

    # QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    from flask import url_for
    try:
        verify_url = url_for('events.view', event_id=event.id, _external=True)
    except RuntimeError:
        verify_url = f"http://127.0.0.1:5000/events/{event.id}"
        
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#5C2C16", back_color="#FDF8ED") # UI colors for QR code too
    
    qr_buffer = BytesIO()
    img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    
    Story.append(Paragraph("Verification QR Code:", styles['Heading3']))
    Story.append(Spacer(1, 6))
    Story.append(Image(qr_buffer, width=120, height=120, hAlign='LEFT'))

    # Define background drawing function
    def draw_background(canvas, doc):
        canvas.saveState()
        # Use a very subtle GMU Gold tinted background instead of plain white/grey
        canvas.setFillColor(colors.HexColor('#FCF8F2')) 
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        
        # Add a border to the page for a more certificate-like appearance using Betel Nut Brown
        canvas.setStrokeColor(colors.HexColor('#5C2C16'))
        canvas.setLineWidth(3)
        canvas.rect(20, 20, doc.pagesize[0]-40, doc.pagesize[1]-40, fill=0, stroke=1)
        
        # Inner border
        canvas.setStrokeColor(colors.HexColor('#E3B559'))
        canvas.setLineWidth(1)
        canvas.rect(25, 25, doc.pagesize[0]-50, doc.pagesize[1]-50, fill=0, stroke=1)
        
        canvas.restoreState()

    # Build PDF
    doc.build(Story, onFirstPage=draw_background, onLaterPages=draw_background)
    pdf_out = buffer.getvalue()
    buffer.close()
    return pdf_out
