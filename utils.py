# utils.py
import os
import smtplib
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import traceback

# -----------------------------
# Config: env / Streamlit / fallback to provided creds
# -----------------------------
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# Prefer env/st.secrets; fallback to the credentials you shared
EMAIL_USER = os.environ.get("EMAIL_USER") or os.environ.get("SMTP_USERNAME") or "noreplyclaimsacknowledgement@gmail.com"
EMAIL_PASS = os.environ.get("EMAIL_PASS") or os.environ.get("SMTP_PASSWORD") or "ncql uouh bkmz nuiv"  # Gmail App Password (16 chars)
FROM_NAME  = os.environ.get("FROM_NAME", "Expense Claims")

def _connect_smtp():
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    return server

def send_email(recipient_email: str, subject: str, body: str, from_name: str | None = None) -> bool:
    """
    Sends a plain-text email via Gmail SMTP.
    Returns True on success, False otherwise (prints error).
    """
    sender_disp = formataddr((from_name or FROM_NAME, EMAIL_USER))

    msg = MIMEMultipart()
    msg["From"] = sender_disp
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = _connect_smtp()
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {recipient_email} | {subject}")
        return True
    except Exception as e:
        print("❌ Error sending email:", e)
        traceback.print_exc()
        return False


# -----------------------------
# Draft builders
# -----------------------------
def _fmt_amount(val, currency="INR"):
    try:
        return f"{currency} {float(val):,.2f}"
    except Exception:
        return f"{currency} {val}"

def draft_employee_ack_on_upload(
    *,
    claim_id: str,
    employee_name: str | None,
    employee_id: str,
    category: str,
    amount,
    currency: str,
    vendor: str | None,
    expense_date: str | None,
    tag: str,               # Auto Approved | Rejected | Manager Pending | Finance Pending | Pending
    decision: str | None,   # Approved | Reject | Send to Manager | Send to Finance Team
    comments: str | None,
) -> tuple[str, str]:
    """Subject/body when employee uploads and validation completes."""
    who = employee_name or employee_id
    status_line = tag
    amt = _fmt_amount(amount, currency or "INR")
    ven = vendor or "Unknown"
    dt  = expense_date or "—"

    subject = f"[Expense Claim ACK] {claim_id} — {status_line}"
    body = (
f"""Hi {who},

We’ve received your expense claim with the details below:

• Tracking ID : {claim_id}
• Category    : {category}
• Amount      : {amt}
• Vendor      : {ven}
• Expense Date: {dt}

Validation Result: {status_line}
Decision        : {decision or '—'}

Comments:
{comments or 'No additional comments'}

You can track this claim in the Claims Dashboard. If this was routed to your Manager or Finance Team, you’ll receive another email when they take action.

Thanks,
{FROM_NAME}
Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    )
    return subject, body


def draft_employee_update_on_action(
    *,
    claim_id: str,
    employee_name: str | None,
    employee_id: str,
    actor_role: str,         # "Manager" or "Finance"
    decision: str,           # "Approve" or "Reject"
    comment: str | None,
) -> tuple[str, str]:
    """Subject/body when manager/finance approves/rejects."""
    who = employee_name or employee_id
    subject = f"[Expense Claim Update] {claim_id} — {decision} by {actor_role}"
    body = (
f"""Hi {who},

Your expense claim has been reviewed.

• Tracking ID : {claim_id}
• Actioned By : {actor_role}
• Decision    : {decision}

Reviewer Comments:
{(comment or 'No reviewer comments')}

Next steps:
• If Approved: the claim will be processed as per policy timelines.
• If Rejected: please check the reviewer comments and resubmit if applicable.

Regards,
{FROM_NAME}
Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    )
    return subject, body
