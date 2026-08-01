import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.colors import Color, black
from reportlab.lib.units import inch

def generate_certificate(attendee_name, event_title, event_date):
    """
    Generate a PDF certificate using ReportLab in-memory.
    Returns the raw PDF bytes.
    """
    buffer = io.BytesIO()
    
    # Create landscape canvas
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Draw border
    c.setStrokeColorRGB(0.1, 0.2, 0.4)
    c.setLineWidth(10)
    c.rect(0.5*inch, 0.5*inch, width - 1*inch, height - 1*inch)
    
    c.setStrokeColorRGB(0.8, 0.6, 0.2)
    c.setLineWidth(2)
    c.rect(0.6*inch, 0.6*inch, width - 1.2*inch, height - 1.2*inch)

    # Title
    c.setFont("Helvetica-Bold", 36)
    c.setFillColorRGB(0.1, 0.2, 0.4)
    c.drawCentredString(width/2.0, height - 2*inch, "CERTIFICATE OF ATTENDANCE")

    # Subtitle
    c.setFont("Helvetica", 16)
    c.setFillColor(black)
    c.drawCentredString(width/2.0, height - 2.8*inch, "This is to certify that")

    # Attendee Name
    c.setFont("Helvetica-Bold", 28)
    c.setFillColorRGB(0.1, 0.2, 0.4)
    c.drawCentredString(width/2.0, height - 3.8*inch, str(attendee_name).upper())

    # Text body
    c.setFont("Helvetica", 16)
    c.setFillColor(black)
    c.drawCentredString(width/2.0, height - 4.6*inch, "has successfully participated in the event:")

    # Event Name
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.8, 0.6, 0.2)
    c.drawCentredString(width/2.0, height - 5.4*inch, str(event_title))

    # Event Date
    c.setFont("Helvetica", 14)
    c.setFillColor(black)
    if isinstance(event_date, str):
        date_str = event_date
    else:
        date_str = event_date.strftime("%B %d, %Y")
    
    c.drawCentredString(width/2.0, height - 6.2*inch, f"Held on {date_str}")

    # Signatures
    c.setFont("Helvetica", 12)
    c.line(1.5*inch, 1.5*inch, 3.5*inch, 1.5*inch)
    c.drawCentredString(2.5*inch, 1.3*inch, "Event Organizer")

    c.line(width - 3.5*inch, 1.5*inch, width - 1.5*inch, 1.5*inch)
    c.drawCentredString(width - 2.5*inch, 1.3*inch, "Faculty Coordinator")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()
