from configparser import ConfigParser
from argparse import ArgumentParser
from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler
from scraper import subdomains, longest_page, most_common_words


def print_summary():
    print("\n=== FINAL SUMMARY ===")
    total_unique_pages = sum(len(v) for v in subdomains.values())
    print(f"Number of unique pages: {total_unique_pages}")
    print()
    print(f"Longest page URL: {longest_page['url']}")
    print(f"Longest page word count: {longest_page['word_count']}")
    print()
    print("Most Common Words: 0. - Word - Count")
    for i, (freq, word) in enumerate(most_common_words.get_top_words()):
        print(f"{i + 1}. - {word} - {freq}")


def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()
    print_summary()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
