import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
import heapq

class MostCommonWords:
    def __init__(self, top_n=50, pages_to_update=50):
        self.top_n = top_n
        self.counter = Counter()  # Global word frequency counter
        self.min_heap = []  # Min-heap to store the top 'n' most common words
        self.pages_processed = 0  # Track the number of pages processed
        self.pages_to_update = pages_to_update  # How often to recalculate top N

    def update(self, words):
        
        # Update the global counter with the word frequencies
        self.counter.update(words)
        
        # Increment the page count
        self.pages_processed += 1
        
        # Recalculate top N words if the threshold has been reached
        if self.pages_processed % self.pages_to_update == 0:
            self.recalculate_top_n()

    #THIS FUNCTION WAS ADDED so the memory load is never too high
    def recalculate_top_n(self):
        # Recalculate the top 'n' words based on the global word counts
        # Get the most common words from the counter
        top_words = self.counter.most_common(self.top_n)
        
        # Clear the current min heap and refill it with the top 'n' words
        self.min_heap = [(freq, word) for word, freq in top_words]

    def get_top_words(self):
        # Return the top 'n' words sorted by frequency
        return sorted(self.min_heap, reverse=True)

    def get_word_count(self):
        # Return the count of the top 'n' words
        return {word: freq for freq, word in self.min_heap}

subdomains = defaultdict(set)

most_common_words = MostCommonWords(top_n=50, pages_to_update=10)

stop_words = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", 
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", 
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", 
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", 
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", 
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", 
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", 
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", 
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", 
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", 
    "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", 
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", 
    "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", 
    "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", 
    "yourself", "yourselves"
}

longest_page = {
    'url': None,
    'word_count': 0
}

def scraper(url, resp):
    links = extract_next_links(url, resp)

    #NUMBER OF UNIQUE PAGES: len(links)
    #LONGEST PAGE: longest_page dict
    #50 MOST COMMON WORDS: most_common_words.get_top_words() and most_common_wordss.get_word_count()

    global subdomains #keeps track of subdomains and the number of unique paths

    links = [link for link in links if is_valid(link)]

    for url in links:
        parsed = urlparse(url)
        subdomains[parsed.netloc].add(parsed.path)

    return links

def extract_next_links(url, resp):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    global stop_words
    global longest_page
    links = set()

    if (resp.status == 200): # No problem
        content = resp.raw_response.content.decode('utf-8', 'ignore')

        soup = BeautifulSoup(content, "html.parser")

        # Extract text and remove unwanted parts like script and style
        # Gather raw words for longest page analysis
        # ASSUMING stopwords count for longest page, as specifications DID NOT specify otherwise
        text = soup.get_text(" ", strip=True)
        words = text.split()  # Split the text by spaces to count words
        #check if current page is longest page
        if longest_page["word_count"] < len(words):
            longest_page["url"] = resp.url
            longest_page["word_count"] = len(words)
        # Gather valid words for common word analysis
        # ASSUMING common_words cannot be less than 2 letters AND cannot be stop_words
        common_words = [word.lower() for word in words if len(word) >= 2 and word.lower() not in stop_words]
        # Update the MostCommonWords instance with the common words for this page
        most_common_words.update(common_words)
        #gather other links from the page
        for a_tag in soup.find_all("a", href=True):
            try:
                full_url = urljoin(url, a_tag['href']) # Resolve relative URLs
                full_url = full_url.split('#')[0]  # Remove fragment
                links.add(full_url)
            except ValueError:
                print ("ValueError for ", a_tag['href'])
        
    else:
        print("Error: ", resp.error)  
        
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]): # schemes to ignore
            return False

        if re.search(r"/events/|/~eppstein/pix|/doku.php/", parsed.path.lower()): # paths to exclude
            return False
        
        if re.search(r"\?share=|\?ical=", parsed.query): # query parameters to exclude
            return False

        isUCIEDU = re.search(r"ics.uci.edu|cs.uci.edu|informatics.uci.edu|stat.uci.edu", parsed.netloc.lower()) #filter for UCI EDU links 

        if isUCIEDU:
            return not re.match(                                        #filter for file extensions to exclude
            r".*\.(css|js|bmp|gif|jpe?g|jpg|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
        
        else:
            return False

    except ValueError:
        print ("ValueError for ", parsed)

    except TypeError:
        print ("TypeError for ", parsed)
        raise
