from flask import Blueprint, request
import requests
import traceback
fetcher_blueprint = Blueprint('fetcher', __name__)
@fetcher_blueprint.route('', methods=['GET', 'POST'])
def fetch_and_show():
    url = None
    if request.method == 'POST':
        url = request.form.get('url') or (request.json and request.json.get('url'))
    else:
        url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print("Exception details:")
        traceback.print_exc()
        return f"Error fetching or parsing data: {e}", 500