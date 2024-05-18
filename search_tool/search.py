import time
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import json
import os
from urllib.parse import urljoin, urlparse, urldefrag
import re
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))

def normalize_url(url):
    url = urldefrag(url)[0]
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    if normalized_url.endswith('/'):
        normalized_url = normalized_url[:-1]
    return normalized_url

def clean_text(text):
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
    inverted_index = defaultdict(lambda: defaultdict(list))
    word_split_pattern = re.compile(r'\b\w+\b')

    for url, content in page_contents:
        words = word_split_pattern.findall(content.lower())
        for position, word in enumerate(words):
            inverted_index[word][url].append(position)

    print(f"Built inverted index with {len(inverted_index)} unique words.")
    return inverted_index

def save_index(index, file_path):
    with open(file_path, 'w') as f:
        json.dump(index, f)
    print(f"Inverted index saved to {file_path}")

def load_index(file_path):
    if not os.path.exists(file_path):
        print(f"{file_path} does not exist. Initializing an empty index.")
        return defaultdict(lambda: defaultdict(list)), "Initialized empty index"
    
    try:
        with open(file_path, 'r') as f:
            index = json.load(f, object_hook=lambda d: defaultdict(list, d))
            print(f"Index loaded from {file_path}.")
            return index, "Loaded successfully"
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to decode {file_path} due to {str(e)}. Clearing its contents and initializing a new index.")
        clear_index(file_path)
        return defaultdict(lambda: defaultdict(list)), "Failed to load; initialized new index"

def merge_indices(existing_index, new_index):
    for word, urls in new_index.items():
        for url, positions in urls.items():
            existing_index[word][url].extend(positions)
    return existing_index

def find_pages(phrase, index):
    words = phrase.lower().split()
    if all(word in STOP_WORDS for word in words):
        print(f"No pages found containing only stop words.")
        return

    valid_words = [word for word in words if word not in STOP_WORDS]
    if not valid_words:
        print(f"No pages found containing the phrase '{phrase}'.")
        return

    page_scores = defaultdict(lambda: {
        'count': 0,
        'positions': defaultdict(list),
        'phrase_count': 0,
        'phrase_positions': [],
        'individual_counts': defaultdict(int)
    })

    for word in valid_words:
        if word in index:
            for url, positions in index[word].items():
                page_scores[url]['count'] += len(positions)
                page_scores[url]['positions'][word].extend(positions)
                page_scores[url]['individual_counts'][word] += len(positions)

    def count_phrase_occurrences(page_scores, word_count):
        for url, data in page_scores.items():
            word_positions = [sorted(data['positions'][word]) for word in valid_words]
            if any(len(pos) == 0 for pos in word_positions):
                continue

            phrase_positions = []
            pos_indices = [0] * word_count

            while True:
                current_positions = [word_positions[i][pos_indices[i]] for i in range(word_count)]
                if all((current_positions[0] + i) == current_positions[i] for i in range(word_count)):
                    phrase_positions.append(current_positions[0])
                    for i in range(word_count):
                        pos_indices[i] += 1
                        if pos_indices[i] >= len(word_positions[i]):
                            pos_indices[i] = float('inf')

                min_pos = min(current_positions)
                min_index = current_positions.index(min_pos)
                pos_indices[min_index] += 1

                if any(pos_indices[i] >= len(word_positions[i]) for i in range(word_count)):
                    break

            data['phrase_count'] = len(phrase_positions)
            data['phrase_positions'] = phrase_positions

    count_phrase_occurrences(page_scores, len(valid_words))

    phrase_results = []
    individual_results = []

    for url, data in page_scores.items():
        if data['phrase_count'] > 0:
            phrase_results.append((url, data))
        else:
            individual_results.append((url, data))

    if phrase_results:
        phrase_results.sort(key=lambda item: (min(item[1]['phrase_positions']), -item[1]['phrase_count'], -item[1]['count']))
        print(f"Pages containing '{phrase}':")
        for page, data in phrase_results:
            print(f"  - {page}\n    │\n    └──('{phrase}' count: {data['phrase_count']}, positions: {data['phrase_positions']})\n")

    if individual_results:
        individual_results.sort(key=lambda item: (min([pos for positions in item[1]['positions'].values() for pos in positions]), -item[1]['count']))
        print(f"\nPages containing individual words from '{phrase}':")
        for page, data in individual_results:
            if any(page == result[0] for result in phrase_results):
                continue
            if data['count'] > 0:
                word_count_details = ", ".join([f"{word}: {data['individual_counts'][word]}, positions: {data['positions'][word]}" for word in valid_words])
                print(f"  - {page}\n    │\n    └──(total count: {data['count']}, {word_count_details})\n")


def print_index(word, index):
    word = word.lower()
    if word in index:
        print(f"Inverted index for '{word}':")
        
        # Extract and sort entries by count and position
        entries = [(url, positions) for url, positions in index[word].items()]
        sorted_entries = sorted(entries, key=lambda item: (-len(item[1]), item[1][0]))

        for url, positions in sorted_entries:
            print(f"  - {url}\n    (count: {len(positions)}, positions: {positions})")
    else:
        print(f"No entries found for '{word}'. The 'print' command only supports single words, not phrases. Use 'find' for phrases.")


def clear_index(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    print(f"Cleared the index file {file_path}")

def print_usage():
    print("Available commands:")
    print("  build             - Crawl the website, build the index, and save it to index.json.")
    print("  load              - Load the index from index.json.")
    print("  print <word>      - Print the inverted index for a specific word. (Single words only)")
    print("  find <phrase>     - Find pages containing the specified phrase.")
    print("  exit              - Exit the program.")

def test_crawl_and_index():
    start_url = "https://quotes.toscrape.com"
    print("Starting the build process...")
    index_file = 'index.json'
    clear_index(index_file)

    pages = crawl_website(start_url, delay=0)
    index = build_inverted_index(pages)
    save_index(index, index_file)

    unique_urls = {url for url, _ in pages}
    expected_page_count = 214
    assert len(unique_urls) == expected_page_count, f"Expected {expected_page_count} pages, but got {len(unique_urls)}"

    print(f"Indexed {len(unique_urls)} pages.")

def main():
    index = None
    index_file = 'index.json'

    print_usage()

    while True:
        command = input("\nEnter a command: ").strip().lower()

        if command == 'build':
            start_url = "https://quotes.toscrape.com"
            print("Starting the build process...")
            existing_index, _ = load_index(index_file)
            existing_urls = {url for urls in existing_index.values() for url in urls}
            pages = crawl_website(start_url, delay=0, existing_urls=existing_urls)
            if not pages:
                print("No new pages found. Index remains unchanged.")
            else:
                new_index = build_inverted_index(pages)
                index = merge_indices(existing_index, new_index)
                save_index(index, index_file)
                unique_urls = {url for url, _ in pages}
                print(f"Indexed {len(unique_urls)} pages.")
        elif command == 'load':
            index, message = load_index(index_file)
            print(message)
        elif command.startswith('print'):
            if index is None:
                print("Index not loaded. Use 'load' command first.")
                continue
            try:
                _, word = command.split(maxsplit=1)
                print_index(word, index)
            except ValueError:
                print("Usage: print <word>")
        elif command.startswith('find'):
            if index is None:
                print("Index not loaded. Use 'load' command first.")
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

        print_usage()

if __name__ == "__main__":
    main()