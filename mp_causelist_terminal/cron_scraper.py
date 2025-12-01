import sys
sys.path.insert(0, '/var/www/mml_python_code')
from mp_manually import fetch_mp_causelist
from datetime import datetime, timedelta, date
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(subject, body):
    host = "email-smtp.us-west-2.amazonaws.com"
    port = 587
    username = "AKIAXZ2CHOT75B53GBNN"
    password = "BHw8IFHZsCr+5IKgXP04oDhU2P846oQSVcWY5IgllILj"

    from_email = "deepak@managemylawsuits.com"
    to_email = ["sanjai@jbkinfotech.com","manoj@jbkinfotech.com"]
    # to_email = ["sanjai@jbkinfotech.com"]

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)


def run_scheduled_scraper(target="tomorrow", send_mail=False):
    benches = ["01", "02", "03"]
    # benches = ["03"]
    bench_city = {
        "01": "Jabalpur",
        "02": "Indore",
        "03": "Gwalior"
    }

    run_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    today_date = date.today()
    target_date = today_date if target.lower() == "today" else today_date + timedelta(days=1)
    date_string = target_date.strftime("%d-%m-%Y")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] CRON TASK STARTED for {date_string}")

    report_lines = [
        f"MP Cause List Daily Report - {date_string}",
        f"Report generated at: {run_time}",
        ""
    ]

    for bench in benches:
        city = bench_city.get(bench, f"Bench-{bench}")
        try:
            result = fetch_mp_causelist(date_string, bench, refresh=True)
            count = sum(len(item.get("clist", [])) for item in result.get("results", []))
            line = f"{city} - {bench} : {count}"
            print(f"{line}")
            report_lines.append(line)
        except Exception as e:
            line = f"{city} - {bench} : Error - {e}"
            print(line)
            report_lines.append(line)

    report_lines.append("")
    body = "\n".join(report_lines)
    subject = f"MP Cause List Daily Report - {date_string}"

    print("Subject:", subject)
    print("Body:\n", body)

    if send_mail:
        send_email(subject, body)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] CRON TASK COMPLETED")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_scheduled_scraper(sys.argv[1], send_mail=True)
    else:
        run_scheduled_scraper("tomorrow", send_mail=True)