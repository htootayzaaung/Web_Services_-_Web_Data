import requests
import getpass
import sys
import datetime
import shlex
import concurrent.futures

session = requests.Session()
current_user = {'is_logged_in': False, 'username': None, 'name': None, 'api_base_url': None}

def login(api_url):
    global current_user
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    # Construct the login URL based on the user's input
    login_url = f"{api_url}/api/login" if not api_url.endswith('/api/login') else api_url
    
    response = session.post(login_url, data={'username': username, 'password': password})
    
    if response.status_code == 200:
        # Handle text response
        welcome_message = response.text
        print(welcome_message)
        current_user['is_logged_in'] = True
        current_user['username'] = username
        current_user['api_base_url'] = api_url  # Store the API base URL

        # Extract name from the welcome message
        name_start = welcome_message.find(",") + 2  # Adjust the index as per your message format
        name_end = welcome_message.find("!", name_start)
        current_user['name'] = welcome_message[name_start:name_end] if name_start < name_end else None
    else:
        # Print the error message as plain text
        print(response.text)

def logout():
    global current_user, session
    if not current_user['is_logged_in']:
        print("No user is logged in.")
        return
    
    # Assuming api_base_url is correctly stored when logging in,
    # and it does not end with a slash.
    logout_url = f"{current_user['api_base_url'].rstrip('/')}/api/logout"
    
    # Assuming that CSRF token handling is required for the logout to succeed.
    # Retrieve CSRF token from the cookies if present; otherwise, set to None.
    csrf_token = session.cookies.get('csrftoken')
    
    headers = {}
    if csrf_token:
        headers['X-CSRFToken'] = csrf_token
        headers['Referer'] = current_user['api_base_url']  # Some servers check the Referer header for CSRF protection.

    response = session.post(logout_url, headers=headers)
    
    if response.status_code in [200, 204]:  # Logout success
        print("Successfully logged out.")
        # Reset current_user and clear session cookies to clean up the session state.
        current_user = {'is_logged_in': False, 'username': None, 'name': None, 'api_base_url': None}
        session.cookies.clear()
    else:
        print(f"Logout failed: {response.status_code} - {response.text}")

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

    # Construct the story posting URL based on the stored API base URL
    api_base_url = current_user['api_base_url'].rstrip('/')
    post_url = f"{api_base_url}/api/stories"

    # Prepare headers including CSRF token and Referer
    csrf_token = session.cookies.get('csrftoken')
    headers = {'Content-Type': 'application/json'}  # Explicitly state the content type
    if csrf_token:
        headers['X-CSRFToken'] = csrf_token
    headers['Referer'] = api_base_url

    response = session.post(post_url, json=story_data, headers=headers)

    if response.status_code == 201:
        print("Story posted successfully.")
    else:
        # When not successful, directly show the status and response
        print(f"Failed to post story: {response.status_code} - {response.text}")
        if response.status_code != 200:  # If there's an error, try to parse and display it
            try:
                error_message = response.json()
                formatted_errors = ", ".join([f"{k}: {', '.join(v)}" for k, v in error_message.items()])
                print("Failed to post story due to the following errors:")
                print(formatted_errors)
            except Exception as e:
                print("Error parsing the failure response.")


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
    date_formats = [
        "%d/%m/%Y", "%Y-%m-%d",  # Original formats
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 format
        "%Y-%m-%d %H:%M:%S.%f+00:00",  # Timestamp with timezone
    ]
    for fmt in date_formats:
        try:
            return datetime.datetime.strptime(date_string, fmt).date()
        except (ValueError, TypeError):
            continue  # Skip to the next format if parsing fails
    # If no format matched, return None or raise a custom exception to handle upstream
    print(f"Warning: Date {date_string} is not in a recognized format. Skipping this story.")
    return None

def fetch_stories(session, url):
    try:
        response = session.get(url)
        if response.status_code == 200:
            try:
                stories_response = response.json()  # Attempt to parse JSON
                #print(stories_response, "\n")
                # Ensure the response is in the expected format (dict with a 'stories' key)
                if isinstance(stories_response, dict) and 'stories' in stories_response:
                    return stories_response['stories']
                else:
                    # If not, log and skip
                    print(f"Warning: Unexpected response format from {url}. Expected a dict with 'stories'. Skipping.")
                    return []
            except ValueError:
                # Handle cases where the response is not valid JSON
                print(f"Warning: Failed to decode JSON response from {url}. Skipping.")
                return []
        else:
            print(f"Warning: Received non-200 response from {url}: {response.status_code}. Skipping.")
            return []
    except Exception as e:
        print(f"Error fetching stories from {url}: {e}. Skipping.")
        return []

def get_news_from_service(id=None, category="*", region="*", news_date="*"):
    pythonanywhere_urls = []
    agency_details = {}

    # Fetching agency URLs and details
    url = "http://newssites.pythonanywhere.com/api/directory/"
    response = requests.get(url)
    if response.status_code == 200:
        agencies = response.json()
        
        # Limit the number of agencies to 20
        agencies = agencies[:20]
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
            user_date = datetime.datetime.strptime(news_date, "%d/%m/%Y").date()
            filtered_stories = []

            for story in all_stories:
                # Check if 'story_date' key exists; if not, skip to the next story
                if 'story_date' not in story or not story['story_date']:
                    print(f"Warning: Missing 'story_date' for story {story.get('key', 'N/A')}. Skipping this story.")
                    continue

                try:
                    # Proceed with parsing since 'story_date' exists
                    story_date = parse_date(story['story_date'])
                    if story_date is None:
                        continue  # If parsing returns None, skip this story

                    if story_date >= user_date:
                        filtered_stories.append(story)
                except ValueError as e:
                    print(f"Error parsing date from story {story['key']}: {e}")
                    continue  # Skip this story on error

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
            #print(story, "\n")
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

    # Use the api_base_url from current_user for dynamic API URL handling
    api_base_url = current_user['api_base_url']
    delete_url = f"{api_base_url}stories/{story_id}" if api_base_url.endswith('/') else f"{api_base_url}/stories/{story_id}"

    # Retrieve CSRF token from session cookies
    csrf_token = session.cookies.get('csrftoken')

    # Include CSRF token in request headers
    headers = {'X-CSRFToken': csrf_token} if csrf_token else {}

    response = session.delete(delete_url, headers=headers)

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
            print(f"API URL: {current_user['api_base_url']}")
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
            logout()
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