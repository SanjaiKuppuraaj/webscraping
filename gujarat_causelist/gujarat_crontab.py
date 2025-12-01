import sys
import datetime
from gujarat_causelist import process_causelist
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body):
    host = "email-smtp.us-west-2.amazonaws.com"
    port = 587
    username = "AKIAXZ2CHOT75B53GBNN"
    password = "BHw8IFHZsCr+5IKgXP04oDhU2P846oQSVcWY5IgllILj"

    from_email = "deepak@managemylawsuits.com"
    to_email = "sanjai@jbkinfotech.com"

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
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


if __name__ == "__main__":
    send_mail_flag = True
    day_choice = sys.argv[1].lower() if len(sys.argv) > 1 else "tomorrow"

    if day_choice == "today":
        target_date = datetime.date.today()
    elif day_choice == "tomorrow":
        target_date = datetime.date.today() + datetime.timedelta(days=1)
    else:
        print("Invalid argument! Use 'today' or 'tomorrow'")
        sys.exit(1)

    formatted_date = target_date.strftime("%d/%m/%Y")
    print(f"Processing Gujarat causelist for {formatted_date}")

    # Get causelist data and total cases directly
    try:
        causelist_data, total_cases = process_causelist(formatted_date)
    except Exception as e:
        print(f"Error processing causelist: {e}")
        causelist_data, total_cases = None, 0

    if causelist_data is None:
        print("No causelist data found.")

    now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    subject = f"Gujarat High Court - {formatted_date}"
    body = (
        f"Gujarat High Court Daily report - {formatted_date}\n"
        f"Report generated at: {now_str}\n"
        f"Total cases: {total_cases}"
    )

    print(subject)
    print(body)

    if send_mail_flag:
        send_email(subject, body)
    else:
        print("Send mail flag is False. Email not sent.")
