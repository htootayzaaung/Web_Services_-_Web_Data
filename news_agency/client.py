import requests
import getpass
import sys
import datetime
import shlex

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
        print("Login failed. Please check username and password.")

def logout(api_base_url):
    global current_user, session
    if not current_user['is_logged_in']:
        print("No user is logged in.")
        return
    
    # Retrieve CSRF token from session cookies
    csrf_token = session.cookies.get('csrftoken')

    # Include CSRF token in request headers
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}

    response = session.post(api_base_url + 'logout', headers=headers)
    if response.status_code == 200:
        print(f"Logout successful for {current_user['name']} ({current_user['username']}).")
        current_user = {'is_logged_in': False, 'username': None, 'name': None}
        session.cookies.clear()
    else:
        print("Logout failed:", response.text)

def post_story():
    global current_user, session
    valid_categories = ['pol', 'art', 'tech', 'trivia']
    valid_regions = ['uk', 'eu', 'w']

    # Check if the user is logged in
    if not current_user['is_logged_in']:
        print("You must be logged in to post a story.")
        return
    
    # Prompt for story details
    headline = input("Enter headline: ")
    category = input("Enter category: ")
    region = input("Enter region: ")
    details = input("Enter details: ")

    # Validation for category and region
    if category not in valid_categories:
        print(f"Invalid category. Valid categories are: {', '.join(valid_categories)}.")
        return
    if region not in valid_regions:
        print(f"Invalid region. Valid regions are: {', '.join(valid_regions)}.")
        return

    url = API_BASE_URL + "stories"
    
    # Retrieve the CSRF token from session cookies
    csrf_token = session.cookies.get('csrftoken')

    # Include CSRF token in request headers
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
    
    print(f"Debug: Headline - {headline}, Category - {category}, Region - {region}")

    response = session.post(url, json={
        'headline': headline, 
        'category': category.lower(), 
        'region': region.lower(), 
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
    valid_keys = {'id', 'cat', 'reg', 'date'}
    switches = {"id": None, "category": "*", "region": "*", "news_date": "*"}
    invalid_keyword_found = False
    format_error_found = False

    for arg in args:
        if "=" not in arg:
            print(f"Invalid command format: {arg}. Expected format is -key=value.")
            format_error_found = True
            continue

        key, value = arg.split("=", 1)
        key = key.lstrip('-').strip('”“"')

        if key not in valid_keys:
            print(f"Invalid command keyword: {key}")
            invalid_keyword_found = True
            continue

        value = value.strip('”“"')
        if value == "":
            continue

        if key == 'cat':
            switches['category'] = value
        elif key == 'reg':
            switches['region'] = value
        elif key == 'date':
            switches['news_date'] = value
        elif key == 'id':
            switches['id'] = value

    return switches, invalid_keyword_found, format_error_found

def get_news_from_service(id=None, category="*", region="*", news_date="*"):
    pythonanywhere_urls = ["http://127.0.0.1:8000/api/stories"]
    agency_details = {}

    url = "http://newssites.pythonanywhere.com/api/directory/"
    response = requests.get(url)
    if response.status_code == 200:
        agencies = response.json()
        for agency in agencies:
            if ".pythonanywhere.com" in agency['url']:
                base_url = agency['url'].rstrip("/")
                full_url = base_url + "/api/stories"
                pythonanywhere_urls.append(full_url)
                # Store agency details
                agency_details[base_url] = {
                    'name': agency['agency_name'],
                    'url': agency['url'],
                    'code': agency['agency_code']
                }

    session = requests.Session()
    for url in pythonanywhere_urls:
        params = {}
        if id and id.strip():
            params['id'] = id.strip()
        if category and category != "*":
            params['category'] = category.strip()
        if region and region != "*":
            params['region'] = region.strip()
        if news_date and news_date != "*":
            try:
                parsed_date = datetime.datetime.strptime(news_date, "%d/%m/%Y").date()
                params['date'] = parsed_date.isoformat()
            except ValueError:
                print("Invalid date format. Please enter the date in 'dd/mm/yyyy' format.")
                return

        response = session.get(url, params=params)
        if response.status_code == 200:
            stories_response = response.json()
            stories = stories_response.get('stories', [])
            if not stories:
                print("No news stories found with the specified criteria.")
            else:
                for story in stories:
                    # Extract base URL for agency details
                    story_base_url = url.rsplit('/api/stories', 1)[0]
                    agency_info = agency_details.get(story_base_url, {'name': 'N/A', 'url': 'N/A', 'code': 'N/A'})

                    print(f"├── Key: {story.get('key', 'N/A')}")
                    print(f"├── Headline: {story.get('headline', 'N/A')}")
                    print(f"├── Category: {story.get('story_cat', 'N/A')}")
                    print(f"├── Region: {story.get('story_region', 'N/A')}")
                    print(f"├── Date: {story.get('story_date', 'N/A')}")
                    print(f"├── Details: {story.get('story_details', 'N/A')}")
                    print(f"├── Agency Name: {agency_info['name']}")
                    print(f"├── Agency URL: {agency_info['url']}")
                    print(f"└── Agency Code: {agency_info['code']}\n")
        #else:
            #print("Failed to get news:", response.text)


def delete_story(story_id):
    global current_user, session

    if not current_user['is_logged_in']:
        print("You must be logged in to delete a story.")
        return

    url = API_BASE_URL + f"stories/{story_id}"

    # Retrieve CSRF token from session cookies
    csrf_token = session.cookies.get('csrftoken')

    # Include CSRF token in request headers
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}

    response = session.delete(url, headers=headers)

    if response.status_code == 200:
        print("Story deleted successfully.")
    else:
        print("Failed to delete the story:", response.text)

def list_agencies():
    url = "http://newssites.pythonanywhere.com/api/directory/"
    response = requests.get(url)

    if response.status_code == 200:
        agencies = response.json()  # Expecting a direct list here
        for agency in agencies:
            print(f"├── Name: {agency['agency_name']}\n├── URL: {agency['url']}\n└── Code: {agency['agency_code']}\n")
    else:
        print(f"Failed to list agencies: {response.text}")
        
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
                "      -cat: the news category from the following: pol (for politics), art, tech (for technology), or trivia (for trivial)\n"
                "            Assumes '*' if omitted.\n"
                "      -reg: the region for the news from the following: uk (for United Kingdom), eu (for European), or w (for World).\n"
                "            Assumes '*' if omitted.\n"
                "      -date: the date for stories (format: 'dd/mm/yyyy'). Assumes '*' if omitted.\n"
                "  - To delete a story: 'delete <story_id>'\n"
                "  - To exit: 'exit'\n"
                "  - To list agencies: 'list'\n"
                "Command: ")

        try:
            command_parts = shlex.split(command)
        except ValueError as e:
            print("Error in command format:", e)
            continue

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
            news_args, invalid_keyword_found, format_error_found = parse_news_args(command_parts[1:])
            if not invalid_keyword_found and not format_error_found:
                get_news_from_service(**news_args)
            else:
                print("Command not executed due to invalid keyword or format error.")
        elif command_parts[0] == 'delete':
            if len(command_parts) == 2:
                story_id = command_parts[1]
                delete_story(story_id)
            else:
                print("Invalid command format. Expected format is 'delete <story_id>'.")
        elif command_parts[0] == 'list':
            list_agencies()
        elif command_parts[0] == 'exit':
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()

