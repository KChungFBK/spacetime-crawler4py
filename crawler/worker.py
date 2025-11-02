from threading import Thread, Lock
from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time
from urllib.parse import urlparse


class Worker(Thread):
    # 🔹 Shared data across all threads for politeness enforcement
    domain_lock = Lock()
    domain_last_access = {}       # domain → timestamp of last access
    POLITENESS_DELAY = 0.5        # 0.5 second between same-domain requests

    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        
    def _respect_politeness(self, url):
        """
        Enforce at least 0.5 seconds between requests to the same domain
        across all worker threads (per politeness policy).
        """
        domain = urlparse(url).netloc
        with Worker.domain_lock:
            last_access = Worker.domain_last_access.get(domain, 0)
            elapsed = time.time() - last_access
            if elapsed < Worker.POLITENESS_DELAY:
                # Sleep only the remaining time necessary
                time.sleep(Worker.POLITENESS_DELAY - elapsed)
            Worker.domain_last_access[domain] = time.time()

    def run(self):
        """
        Each worker thread continuously fetches URLs from the frontier, 
        downloads pages, extracts links, and adds them back until the 
        frontier is empty.
        """
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            # 🕒 Respect per-domain politeness
            self._respect_politeness(tbd_url)

            # Download the page
            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}."
            )

            # Extract and validate links
            scraped_urls = scraper.scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)

            # Mark the page as complete
            self.frontier.mark_url_complete(tbd_url)

            # Optional: short delay (respects global config delay too)
            time.sleep(self.config.time_delay)