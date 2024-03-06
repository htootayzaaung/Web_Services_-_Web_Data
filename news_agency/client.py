import requests
import getpass
import sys
import datetime

# Base URL of your Django API
API_BASE_URL = "http://127.0.0.1:8000/api/"

session = requests.Session()
current_user = {'is_logged_in': False, 'username': None, 'name': None}

def login(api_url):
    global current_user
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    response = session.post(api_url, data={'username': username, 'password': password})
    
    if response.status_code == 200:
        user_data = response.json()
        current_user['is_logged_in'] = True
        current_user['username'] = username
        current_user['name'] = user_data.get('name')
        print(f"Login successful. Welcome, {current_user['name']} ({username})!")
    else:
        print("Login failed:", response.text)

def logout(api_base_url):
    global current_user, session
    if not current_user['is_logged_in']:
        print("No user is logged in.")
        return
    response = session.post(api_base_url + 'logout')
    if response.status_code == 200:
        print(f"Logout successful for {current_user['name']} ({current_user['username']}).")
        current_user = {'is_logged_in': False, 'username': None, 'name': None}
        session.cookies.clear()
    else:
        print("Logout failed:", response.text)

def post_story():
    global session
    url = API_BASE_URL + "stories"
    
    # Retrieve the CSRF token from session cookies
    csrf_token = session.cookies.get('csrftoken')

    headline = input("Enter headline: ")
    category = input("Enter category: ")
    region = input("Enter region: ")
    details = input("Enter details: ")

    # Include CSRF token in request headers
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}

    response = session.post(url, json={
        'headline': headline, 
        'category': category, 
        'region': region, 
        'details': details
    }, headers=headers)

    if response.status_code == 201:
        print("Story posted successfully.")
    else:
        error_message = response.json()
        formatted_errors = []

        # Iterate through the errors and create a user-friendly message
        for field, messages in error_message.items():
            # For fields with choices like 'category' and 'region', provide the valid choices
            if field in ['category', 'region']:
                valid_choices = {
                    'category': ['pol', 'art', 'tech', 'trivia'],
                    'region': ['uk', 'eu', 'w']
                }
                formatted_errors.append(f"{field.capitalize()} error: {', '.join(messages)}. Valid choices are: {', '.join(valid_choices[field])}.")
            else:
                # Generic error formatting for other fields
                formatted_errors.append(f"{field.capitalize()} error: {', '.join(messages)}.")

        # Join all the error messages into one string and print it
        print("Failed to post story due to the following errors:")
        print("\n".join(formatted_errors))

def parse_news_args(args):
    switches = {"category": "*", "region": "*", "news_date": "*"}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lstrip('-')
            # Map command line args to function kwargs
            if key == 'cat':
                key = 'category'
            elif key == 'reg':
                key = 'region'
            elif key == 'date':
                key = 'news_date'
            if key in switches:
                switches[key] = value.strip('”“')
    return switches


def get_news_from_service(news_id=None, category="*", region="*", news_date="*"):
    # Construct the URL with optional parameters
    url = f"{API_BASE_URL}stories"
    params = {}
    if news_id:
        params['id'] = news_id
    if category != "*":
        params['cat'] = category
    if region != "*":
        params['reg'] = region
    if news_date != "*":
        # Convert the date to the API's expected format
        try:
            news_date = datetime.datetime.strptime(news_date, "%d/%m/%Y").date()
            params['date'] = news_date.isoformat()
        except ValueError:
            print("Invalid date format. Please enter the date in 'dd/mm/yyyy' format.")
            return

    response = session.get(url, params=params)
    if response.status_code == 200:
        stories = response.json()
        for story in stories:
            print(f"ID: {story['id']}")
            print(f"Headline: {story['headline']}")
            print(f"Category: {story['category']}")
            print(f"Region: {story['region']}")
            print(f"Author: {story.get('author_name', 'N/A')}")
            print(f"Date: {story['date']}")
            print(f"Details: {story['details']}\n")
    else:
        print("Failed to get news:", response.text)
        
def main():
    while True:
        if current_user['is_logged_in']:
            print(f"\nLogged in as: {current_user['name']} ({current_user['username']})")
        else:
            print("\nPlease log in!")
            
        command = input("\nEnter command: \n"
                "  - To login: 'login <API URL>'\n"
                "  - To logout: 'logout'\n"
                "  - To post a story: 'post'\n"
                "  - To get news: 'news [-id=] [-cat=] [-reg=] [-date=]' (e.g., 'news -cat=tech -reg=uk')\n"
                "    where [-id], [cat], [reg], and [date] are optional switches that have the following effects:\n"
                "      -id: the id of the news service. Collects from all if omitted.\n"
                "      -cat: the news category (e.g., 'tech'). Assumes '*' if omitted.\n"
                "      -reg: the region of the stories (e.g., 'uk'). Assumes '*' if omitted.\n"
                "      -date: the date for stories (format: 'dd/mm/yyyy'). Assumes '*' if omitted.\n"
                "  - To exit: 'exit'\n"
                "Command: ")
        command_parts = command.split()
        args = command_parts[1:]
        
        if not command_parts:
            print("No command entered.")
            continue
        if command_parts[0] == 'login' and len(command_parts) == 2:
            login(command_parts[1])
        elif command_parts[0] == 'logout':
            logout(API_BASE_URL)
        elif command_parts[0] == 'post':
            post_story()
        elif command_parts[0] == 'news':
            news_args = parse_news_args(args)
            get_news_from_service(**news_args)
        elif command_parts[0] == 'exit':
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()

