import requests

# Base URL of your Django API
API_BASE_URL = "http://127.0.0.1:8000/api/"

def login():
    url = f"{API_BASE_URL}login"
    username = input("Enter username: ")
    password = input("Enter password: ")
    response = requests.post(url, data={'username': username, 'password': password})
    if response.status_code == 200:
        print("Login successful.")
    else:
        print("Login failed:", response.text)

def logout():
    url = f"{API_BASE_URL}logout"
    response = requests.post(url)
    if response.status_code == 200:
        print("Logout successful.")
    else:
        print("Logout failed:", response.text)

def post_story():
    url = f"{API_BASE_URL}stories"
    headline = input("Enter headline: ")
    category = input("Enter category: ")
    region = input("Enter region: ")
    details = input("Enter details: ")
    response = requests.post(url, json={
        'headline': headline, 
        'category': category, 
        'region': region, 
        'details': details
    })
    if response.status_code == 201:
        print("Story posted successfully.")
    else:
        print("Failed to post story:", response.text)

def main():
    while True:
        command = input("Enter command (login, logout, post, exit): ")
        if command == 'login':
            login()
        elif command == 'logout':
            logout()
        elif command == 'post':
            post_story()
        elif command == 'exit':
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
