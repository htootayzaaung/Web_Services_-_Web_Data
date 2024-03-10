import requests
import getpass
import sys
import datetime
import shlex
import concurrent.futures

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
        # Handle text response
        welcome_message = response.text
        print(welcome_message)
        current_user['is_logged_in'] = True
        current_user['username'] = username

        # Extract name from the welcome message
        name_start = welcome_message.find(",") + 2  # Adjust the index as per your message format
        name_end = welcome_message.find("!", name_start)
        current_user['name'] = welcome_message[name_start:name_end] if name_start < name_end else None
    else:
        # Print the error message as plain text
        print(response.text)

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
        print(response.text)  # Display plain text success message
        current_user = {'is_logged_in': False, 'username': None, 'name': None}
        session.cookies.clear()
    else:
        print(f"Logout failed: {response.text}")  # Display plain text error message

def post_story():
    global current_user, session
    valid_categories = ['pol', 'art', 'tech', 'trivia']
    valid_regions = ['uk', 'eu', 'w']

    # Check if the user is logged in
    if not current_user['is_logged_in']:
        print("You must be logged in to post a story.")
        return

    # Prompt for story details
    headline = input("Enter headline: ").strip()
    category = input("Enter category: ").strip().lower()
    region = input("Enter region: ").strip().lower()
    details = input("Enter details: ").strip()

    # Validation for category, region, and details
    if not headline:
        print("Headline cannot be blank!")
        return
    if category not in valid_categories:
        print(f"Invalid category! Valid categories are: {', '.join(valid_categories)}.")
        return
    if region not in valid_regions:
        print(f"Invalid region! Valid regions are: {', '.join(valid_regions)}.")
        return
    if not details:
        print("Story details cannot be blank!")
        return

    story_data = {
        'headline': headline, 
        'story_cat': category, 
        'story_region': region, 
        'story_date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'story_details': details
    }

    url = API_BASE_URL + "stories"
    
    # Retrieve the CSRF token from session cookies
    csrf_token = session.cookies.get('csrftoken')

    # Include CSRF token in request headers
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}

    response = session.post(url, json=story_data, headers=headers)

    if response.status_code == 201:
        print("Story posted successfully.")
    else:
        # Handle non-JSON response as plain text
        if 'application/json' not in response.headers.get('Content-Type', ''):
            print(response.text)
            return

        # Handle JSON response
        error_message = response.json()
        formatted_errors = []
        for field, messages in error_message.items():
            formatted_errors.append(f"{field.capitalize()} error: {', '.join(messages)}.")

        print("Failed to post story due to the following errors:")
        print("\n".join(formatted_errors))



def parse_news_args(args):
    valid_keys = {'id', 'cat', 'reg', 'date'}
    switches = {"id": None, "category": "*", "region": "*", "news_date": "*"}
    invalid_keyword_found = False
    format_error_found = False

    for arg in args:
        if "=" not in arg:
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

def parse_date(date_string):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):  # Add or remove formats as you know are used by the agencies
        try:
            return datetime.datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date {date_string} is not in a recognized format")

def fetch_stories(session, url):
    response = session.get(url)
    if response.status_code == 200:
        stories_response = response.json()
        #print(stories_response, "\n")
        return stories_response.get('stories', [])
    return []

def get_news_from_service(id=None, category="*", region="*", news_date="*"):
    pythonanywhere_urls = ["http://127.0.0.1:8000/api/stories"]
    agency_details = {}

    # Fetching agency URLs and details
    url = "http://newssites.pythonanywhere.com/api/directory/"
    response = requests.get(url)
    if response.status_code == 200:
        agencies = response.json()
        for agency in agencies:
            if ".pythonanywhere.com" in agency['url']:
                base_url = agency['url'].rstrip("/")
                full_url = base_url + "/api/stories"
                pythonanywhere_urls.append(full_url)
                agency_details[base_url] = {
                    'name': agency['agency_name'],
                    'url': agency['url'],
                    'code': agency['agency_code']
                }

    session = requests.Session()
    all_stories = []
    # Use ThreadPoolExecutor to fetch stories in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(pythonanywhere_urls)) as executor:
        future_to_url = {executor.submit(fetch_stories, session, url): url for url in pythonanywhere_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                stories = future.result()
                for story in stories:
                    story_base_url = url.rsplit('/api/stories', 1)[0]
                    agency_info = agency_details.get(story_base_url, {'name': 'N/A', 'url': 'N/A', 'code': 'N/A'})
                    story.update({
                        'agency_name': agency_info['name'],
                        'agency_url': agency_info['url'],
                        'agency_code': agency_info['code']
                    })
                all_stories.extend(stories)
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))

    # Client-side filtering
    if id:
        all_stories = [story for story in all_stories if story.get('agency_code') == id]
    if category != "*":
        all_stories = [story for story in all_stories if story.get('story_cat') == category]
    if region != "*":
        all_stories = [story for story in all_stories if story.get('story_region') == region]
    if news_date != "*":
        try:
            # Parse the user input date from DD/MM/YYYY to a date object
            user_date = datetime.datetime.strptime(news_date, "%d/%m/%Y").date()
            
            # Now, convert the story dates to date objects for comparison
            filtered_stories = []
            for story in all_stories:
                try:
                    # Parse the date from the story using the parse_date function
                    story_date = parse_date(story['story_date'])
                    
                    # If the story date is valid, compare and add to the list
                    if story_date >= user_date:
                        filtered_stories.append(story)
                except ValueError as e:
                    # If parsing fails, log an error and skip the story
                    print(f"Error parsing date from story {story['key']}: {e}")

            all_stories = filtered_stories
            
        except ValueError as e:
            print(f"Error parsing user date: {e}")
            print("Invalid date format. Please enter the date in 'dd/mm/yyyy' format.")
            return
        
    # Printing the stories
    if not all_stories:
        print("No news stories found with the specified criteria.")
    else:
        for story in all_stories:
            print(story, "\n")
            print(f"├── Key: {story.get('key', 'N/A')}")
            print(f"├── Headline: {story.get('headline', 'N/A')}")
            print(f"├── Category: {story.get('story_cat', 'N/A')}")
            print(f"├── Region: {story.get('story_region', 'N/A')}")
            print(f"├── Author: {story.get('author', 'N/A')}")
            print(f"├── Date: {story.get('story_date', 'N/A')}")
            print(f"├── Details: {story.get('story_details', 'N/A')}")
            print(f"├── Agency Name: {story.get('agency_name', 'N/A')}")
            print(f"├── Agency URL: {story.get('agency_url', 'N/A')}")
            print(f"└── Agency Code: {story.get('agency_code', 'N/A')}\n")


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
        if command_parts[0] == 'login':
            if len(command_parts) == 2:
                login(command_parts[1])
            else:
                print("Invalid command format. Expected format is 'login <API URL>'.")
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
