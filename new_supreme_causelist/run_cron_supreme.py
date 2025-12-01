import sys
import os
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE_PATH = "/var/www/mml_python_code/new_supreme_causelist"
sys.path.append(BASE_PATH)

from supreme_courtdata import run_supreme_court_fetch
SEND_MAIL = True
def send_email(subject, body):
    host = "email-smtp.us-west-2.amazonaws.com"
    port = 587
    username = "AKIAXZ2CHOT75B53GBNN"
    password = "BHw8IFHZsCr+5IKgXP04oDhU2P846oQSVcWY5IgllILj"

    from_email = "deepak@managemylawsuits.com"
    to_emails = ["sanjai@jbkinfotech.com", "manoj@jbkinfotech.com"]

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)

def main():
    today = (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y")
    # today = "13-10-2025"
    result = run_supreme_court_fetch(today, update=True)

    results = result.get("results", [])
    total_files = len(results)
    total_cases = 0
    for item in results:
        if isinstance(item, dict) and "result" in item:
            for block in item["result"]:
                if isinstance(block, dict) and "clist" in block:
                    total_cases += len(block["clist"])

    result["total_case_records"] = total_cases

    output_file = f"supreme_court_{today}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    print(f"Total JSON files processed: {total_files}")
    print(f"Total inner case records (clist count): {total_cases}")
    if SEND_MAIL:
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        subject = f"Supreme Court Cause List {today}"
        body = (
            "Supreme Court Cause List Daily Report\n"
            f"Report generated at: {now_str}\n"
            f"Total Cases: {total_cases}\n"
        )
        send_email(subject, body)
    else:
        print("SEND_MAIL is False → Skipping email.")


if __name__ == "__main__":
    main()
