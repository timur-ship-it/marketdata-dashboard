#!/usr/bin/env python3
import smtplib
import getpass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === Your details ===
sender_name = "Timur Vagizov"
company = "EASTGATE ADVISORY SERVICES - FZCO, Dubai UAE"
phone = "+971589802649"
email = "timur@konex.ae"

# === Vendors ===
vendors = {
    "Cbonds": "pro@cbonds.com",
    "Field Gibson Media": "ashton.rowntree@fieldgibsonmedia.com"
}

subject = "Inquiry — Bond/Sukūk Data API Coverage for Specific ISINs"

body = f"""Dear {{vendor_name}} Team,

My name is {sender_name}, and I represent {company}. I am interested in integrating a bond/sukūk data feed into our Python-based analytics and dashboard system.

Below are my requirements:
- Instruments (ISINs):
  XS3065329446, XS2633136234, XS2914525154, XS2841181972, XS3068594129, XS2777443768
- Fields required: price quotes, yield to maturity, outstanding amount (if available), issue date, maturity date
- Frequency: At least end-of-day data, preferably updated daily
- Historical depth: As far back as the series covers
- Delivery format: REST API (JSON/CSV)
- Usage: Internal analysis and dashboarding

Could you please provide the following:
1. Confirmation of coverage and available fields
2. Frequency and latency of updates
3. Pricing tiers for small-scale internal use
4. Delivery details and sample data if possible

Thank you for your assistance.

Best regards,
{sender_name}
{company}
Phone: {phone}
Email: {email}
"""

# === Ask for password securely ===
password = getpass.getpass("Enter your Gmail app password (will not be shown): ")

# === Send emails ===
def send_email(to_addr, vendor_name):
    msg = MIMEMultipart("alternative")
    msg["From"] = email
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body.format(vendor_name=vendor_name), "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email, password)
        smtp.send_message(msg)
        print(f"✅ Sent to {vendor_name} ({to_addr})")

for vendor, addr in vendors.items():
    send_email(addr, vendor)

print("\nAll messages sent successfully via Gmail.")
