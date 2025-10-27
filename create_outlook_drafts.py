#!/usr/bin/env python3
import subprocess

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

body_template = f"""Dear {{vendor_name}} Team,

My name is {sender_name}, and I represent {company}. I am interested in integrating a bond/sukūk data feed into our Python-based analytics and dashboard system.

Below are my requirements:
- Instruments (ISINs):
  XS3065329446, XS2633136234, XS2914525154, XS2841181972, XS3068594129, XS2777443768
- Fields required: price quotes, yield to maturity, outstanding amount (if available), issue date, maturity date
- Frequency: At least end-of-day data, preferably updated daily
- Historical depth: As far back as the series covers (ideally from issuance)
- Delivery format: REST API (JSON/CSV) preferable, or another format you support
- Usage: The data will be used internally for analysis and dashboarding by our team

Could you please provide the following information:
1. Confirmation of coverage: Are the ISINs above included in your database? If yes, which fields are available for each?
2. Frequency and latency of updates: How soon after market close / issuer publication do prices/yields become available?
3. Pricing tiers: What is the cost structure (monthly, annual, per-instrument, minimal tier) for usage at our scale (≈6 instruments)?
4. Delivery details: Which endpoints/formats are supported, limits on requests, any integration support or sample data you provide?

I would appreciate any sample data or sandbox access to evaluate compatibility before committing.

Thank you very much for your assistance. I look forward to your reply.

Best regards,
{sender_name}
{company}
Phone: {phone}
Email: {email}
"""

for vendor, addr in vendors.items():
    body = body_template.format(vendor_name=vendor)

    applescript = f'''
    tell application "Microsoft Outlook"
        set newMsg to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
        make new recipient at newMsg with properties {{email address:{{address:"{addr}"}}}}
        set sender of newMsg to "{email}"
        save newMsg
        activate
    end tell
    '''

    subprocess.run(["osascript", "-e", applescript])
    print(f"✅ Created Outlook draft for {vendor} ({addr})")

print("\nAll messages created inside Outlook → Drafts. Open Outlook to review or send them.")
