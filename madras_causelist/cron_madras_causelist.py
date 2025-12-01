import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from madras_causelist import run_madras_scraper
import sys

def send_email(subject, body):
    host = "email-smtp.us-west-2.amazonaws.com"
    port = 587
    username = "AKIAXZ2CHOT75B53GBNN"
    password = "BHw8IFHZsCr+5IKgXP04oDhU2P846oQSVcWY5IgllILj"

    from_email = "deepak@managemylawsuits.com"
    to_email = ["sanjai@jbkinfotech.com","manoj@jbkinfotech.com"]
    # "manoj@jbkinfotech.com"
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

def run_scheduled_scraper(date_str=None, send_mail=False):
    if not date_str:
        date_obj = datetime.datetime.now() + datetime.timedelta(days=1)
    else:
        date_str = date_str.lower()
        if date_str == "today":
            date_obj = datetime.datetime.now()
        elif date_str == "tomorrow":
            date_obj = datetime.datetime.now() + datetime.timedelta(days=1)
        else:
            date_obj = datetime.datetime.strptime(date_str, "%d-%m-%Y")

    formatted_date = date_obj.strftime("%d-%m-%Y")
    print(f"Running Madras High Court scraper for {formatted_date}...")

    try:
        result = run_madras_scraper(formatted_date, update=True)
        total_cases = result.get("total_count", 0)
        print(f"Scraper completed. Total cases: {total_cases}")

        if send_mail:
            subject = f"Madras HC Scraper Report – {formatted_date}"
            body = f"Madras High Court Causelist"
            boby = body +"\n" +f"Report generated at: {formatted_date}"
            body = boby +"\n"+f"Scraper completed successfully.\nTotal cases: {total_cases}"
            send_email(subject, body)

    except Exception as e:
        error_msg = f"Error while scraping: {e}"
        print(error_msg)
        if send_mail:
            send_email(f"Scraper Error – {formatted_date}", error_msg)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_scheduled_scraper(sys.argv[1], send_mail=True)
    else:
        run_scheduled_scraper(send_mail=True)
