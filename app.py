import os
import io
import pandas as pd
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.colors import orange, blue
from flask_qrcode import QRcode
import smtplib
from email.message import EmailMessage


app = Flask(__name__, static_folder='static')
app.secret_key = 'CHANGE_ME'
QRcode(app)

UPLOAD_FOLDER = 'uploads'
CERT_FOLDER = 'certificates'
BACKGROUND_IMAGE = 'background.jpg'
SIGNATURE_IMAGE = 'signature.png'

EMAIL_SENDER = 'your.email@gmail.com'
EMAIL_PASSWORD = 'YOUR_APP_PASSWORD'
EMAIL_SMTP = 'smtp.gmail.com'
EMAIL_PORT = 587

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CERT_FOLDER, exist_ok=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['excel']
        if not file:
            flash("No file selected!", "error")  # ✅ Error flash
            return redirect(request.url)
            # return "No file uploaded!"
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        df = pd.read_excel(path)
        for _, row in df.iterrows():
            generate_certificate(
                name=row["Name"],
                regno=row["RegisterNumber"],
                course=row["Course"],
                from_date=row["FromDate"],
                to_date=row["ToDate"],
                college=row["CollegeName"],
                department=row["Department"],
                degree=row["Degree"],
                duration=row["Duration"]
            )
        flash("Certificates generated successfully!", "success")
        return redirect(url_for('certificates'))
    return render_template('index.html')


def generate_certificate(name, regno, course, from_date, to_date, degree, department, college, duration):
    from datetime import datetime

    width, height = A4
    output_file = os.path.join("certificates", f"{name.replace(' ', '_')}.pdf")
    bg_img = ImageReader("certificate.jpg")

    from_date_fmt = pd.to_datetime(from_date).strftime("%d/%m/%Y")
    to_date_fmt = pd.to_datetime(to_date).strftime("%d/%m/%Y")
    today = datetime.today().strftime("%d %B %Y")

    c = canvas.Canvas(output_file, pagesize=A4)
    c.drawImage(bg_img, 0, 0, width=width, height=height)

    # Header info
    c.setFont("Helvetica", 12)
    c.drawRightString(width - 40, height - 100, "+91 8189898884")
    c.drawRightString(width - 40, height - 120,
                      "hr@by8labs.com")
    c.drawRightString(width - 40, height - 140,
                      "www.by8labs.com")

    c.setFont("Helvetica", 14)
    c.drawRightString(width - 40, height - 200, today)

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 280,
                        "TO WHOMSOEVER IT MAY CONCERN")

    # Paragraph Style
    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        'Justify',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=18,
        alignment=TA_JUSTIFY
    )

    # Content
    content = f"""
    &nbsp;&nbsp;&nbsp;&nbsp;This is to certify that <b>{name}</b>, bearing Register Number <b>{regno}</b>, currently pursuing {degree} in the Department of {department} <b>{college}</b>, Pudukkottai, has successfully completed an internship at Inno <b>BY8LABS</b> Solution Private Limited. The internship was in the domain of {course} and was carried out over a duration of {duration}, from <b>{from_date_fmt} to {to_date_fmt}</b>.<br/>

    &nbsp;&nbsp;&nbsp;&nbsp;During the span, they proved to be punctual and reliable individuals. Their learning abilities are commendable, showing a quick grasp of new concepts. Feedback and evaluations consistently highlighted their strong learning curve. Furthermore, their interpersonal and communication skills are excellent. We take this opportunity to wish them the very best in their future endeavors.
    """

    paragraph = Paragraph(content.strip(), para_style)

    # Frame to hold the paragraph (centered block with margins)
    frame_margin_x = 60  # Left and right padding
    frame_width = width - 2 * frame_margin_x
    frame_height = 330
    frame_y = height - 650  # vertical starting point

    frame = Frame(frame_margin_x, frame_y, frame_width,
                  frame_height, showBoundary=0)
    frame.addFromList([paragraph], c)

    # Signature
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 220, "Best Regards,")
    signature_path = "nancy sign.png"  # use your actual file path
    if os.path.exists(signature_path):
        c.drawImage(signature_path, 60, 180, width=100, height=30, mask='auto')
    c.drawString(60, 165, "Mrs. S. Nancy MCA.,")
    c.setFont("Helvetica", 12)
    c.drawString(60, 150, "HR Manager,")
    c.drawString(60, 135, "BY8LABS Inc,")
    c.drawString(60, 120, "Pudukkottai - 622001")

    c.setFillColor(blue)
    c.rect(0, 55, width, 5, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)

    # Footer address
    footer = [
        "#5861, Santhanathapuram Puram, 7th street, Pudukkottai – 622001. | +91 8189898884.",
        "#08-82, Redhills, Singapore – 150069. | +65 81532542."
    ]
    c.setFont("Helvetica", 12)
    y = 40
    for line in footer:
        c.drawCentredString(width/2, y, line)
        y -= 14

    c.setFillColor(orange)
    c.rect(0, 0, width, 20, fill=1, stroke=0)

    c.save()


@app.route('/certificates')
def certificates():
    data = []
    files = sorted(f for f in os.listdir(CERT_FOLDER) if f.lower().endswith('.pdf'))
    for idx, fname in enumerate(files, 1):
        name = fname.rsplit('.',1)[0].replace('_',' ')
        link = request.host_url + 'download/' + fname
        data.append({'sno':idx, 'name':name, 'filename':fname, 'link':link})
    return render_template('certificates.html', certs=data)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(CERT_FOLDER, filename, as_attachment=True)

@app.route('/send/<filename>', methods=['POST'])
def send_cert(filename):
    email = request.form['email']
    path = os.path.join(CERT_FOLDER, filename)
    if not os.path.isfile(path): flash("File not found", "danger"); return redirect(url_for('certificates'))
    msg = EmailMessage()
    msg['Subject'] = 'Your Certificate'
    msg['From']=EMAIL_SENDER; msg['To']=email
    msg.set_content('Your certificate attached.')
    with open(path,'rb') as f: msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=filename)
    try:
        s=smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT); s.starttls(); s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.send_message(msg); s.quit()
        flash(f"Sent to {email}", "success")
    except Exception as e:
        flash(f"Failed: {e}", "danger")
    return redirect(url_for('certificates'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=True)