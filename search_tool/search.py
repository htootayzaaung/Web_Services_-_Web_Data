import time
import requests
from bs4 import BeautifulSoup
from collections import defaultdict, Counter
import json
import os
from urllib.parse import urljoin, urlparse, urldefrag
import re

def normalize_url(url):
    # Remove URL fragment and normalize
    url = urldefrag(url)[0]
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    # Ensure consistent trailing slash
    if normalized_url.endswith('/'):
        normalized_url = normalized_url[:-1]
    return normalized_url

def clean_text(text):
    # Strip leading and trailing whitespace and collapse multiple spaces
    return ' '.join(text.split())

def crawl_website(start_url, delay=0, existing_urls=None):
    if existing_urls is None:
        existing_urls = set()
    urls_to_crawl = [start_url]
    crawled_urls = set(existing_urls)
    page_contents = []

    while urls_to_crawl:
        url = urls_to_crawl.pop(0)
        normalized_url = normalize_url(url)
        if normalized_url in crawled_urls:
            continue

        print(f"Crawling URL: {url}")

        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator=' ')
            cleaned_text = clean_text(text)
            if cleaned_text:
                page_contents.append((normalized_url, cleaned_text))
                print(f"Text extracted from {normalized_url}: {cleaned_text[:100]}...")  # Debug: Show a snippet of extracted text

            crawled_urls.add(normalized_url)
            for link in soup.find_all('a'):
                new_url = link.get('href')
                if new_url:
                    new_url = urljoin(start_url, new_url)
                    normalized_new_url = normalize_url(new_url)
                    if normalized_new_url not in crawled_urls and urlparse(new_url).netloc == urlparse(start_url).netloc:
                        urls_to_crawl.append(new_url)

            time.sleep(delay)
        else:
            print(f"Failed to retrieve URL: {url} with status code: {response.status_code}")

    return page_contents

def build_inverted_index(page_contents):
    inverted_index = defaultdict(lambda: defaultdict(int))
    word_split_pattern = re.compile(r'\b\w+\b')

    for url, content in page_contents:
        words = word_split_pattern.findall(content.lower())
        word_counts = Counter(words)
        for word, count in word_counts.items():
            inverted_index[word][url] = count

    print(f"Built inverted index with {len(inverted_index)} unique words.")
    return inverted_index

def save_index(index, file_path):
    with open(file_path, 'w') as f:
        json.dump(index, f)
    print(f"Inverted index saved to {file_path}")

def load_index(file_path):
    if not os.path.exists(file_path):
        print(f"{file_path} does not exist. Initializing an empty index.")
        return defaultdict(lambda: defaultdict(int))
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        print(f"Failed to decode {file_path}. Clearing its contents and initializing a new index.")
        clear_index(file_path)
        return defaultdict(lambda: defaultdict(int))

def merge_indices(existing_index, new_index):
    for word, urls in new_index.items():
        for url, count in urls.items():
            existing_index[word][url] += count
    return existing_index

def print_index(word, index):
    word = word.lower()
    if word in index:
        print(f"Inverted index for '{word}':")
        for url, count in index[word].items():
            print(f"  - {url}: {count} occurrences")
    else:
        print(f"No entries found for '{word}'.")

def find_pages(phrase, index):
    words = phrase.lower().split()
    if all(word in index for word in words):
        pages = set(index[words[0]].keys())
        for word in words[1:]:
            pages &= set(index[word].keys())
        if pages:
            print(f"Pages containing '{phrase}':")
            for page in pages:
                print(f"  - {page}")
        else:
            print(f"No pages found containing the phrase '{phrase}'.")
    else:
        print(f"No pages found containing the phrase '{phrase}'.")

def clear_index(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write('')
    print(f"Cleared the index file {file_path}")

def print_usage():
    print("Available commands:")
    print("  build             - Crawl the website, build the index, and save it to index.json.")
    print("  load              - Load the index from index.json.")
    print("  print <word>      - Print the inverted index for a specific word.")
    print("  find <phrase>     - Find pages containing the specified phrase.")
    print("  exit              - Exit the program.")

def main():
    index = None
    index_file = 'index.json'

    print_usage()  # Print usage instructions initially

    while True:
        command = input("\nEnter a command: ").strip().lower()

        if command == 'build':
            start_url = "https://quotes.toscrape.com"
            print("Starting the build process...")

            # Load existing index and get existing URLs
            existing_index = load_index(index_file)
            existing_urls = {url for urls in existing_index.values() for url in urls}

            # Crawl website and merge with existing data
            pages = crawl_website(start_url, delay=0, existing_urls=existing_urls)
            if not pages:
                print("No new pages found. Index remains unchanged.")
            else:
                print("Crawling completed. Building the inverted index...")
                new_index = build_inverted_index(pages)

                # Merge new index with existing index
                index = merge_indices(existing_index, new_index)
                save_index(index, index_file)
                print("Inverted index built and saved to index.json.")
        elif command == 'load':
            index = load_index(index_file)
            print("Index loaded from index.json.")
        elif command.startswith('print'):
            if index is None:
                print("Index not loaded. Use 'load' command first.")
                print_usage()
                continue
            try:
                _, word = command.split(maxsplit=1)
                print_index(word, index)
            except ValueError:
                print("Usage: print <word>")
        elif command.startswith('find'):
            if index is None:
                print("Index not loaded. Use 'load' command first.")
                print_usage()
                continue
            try:
                _, phrase = command.split(maxsplit=1)
                find_pages(phrase, index)
            except ValueError:
                print("Usage: find <phrase>")
        elif command == 'exit':
            print("Exiting the program.")
            break
        else:
            print("Invalid command.")
        
        print_usage()  # Print usage instructions after each command

if __name__ == "__main__":
    main()
