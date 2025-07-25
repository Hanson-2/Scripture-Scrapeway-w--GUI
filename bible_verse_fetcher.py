import requests
from bs4 import BeautifulSoup, Tag
import re
import time

# --- Canonical and Deuterocanonical Books ---
CANONICAL_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms",
    "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"
]
DEUTERO_BOOKS = [
    "Tobit", "Judith", "Additions to Esther", "Wisdom", "Sirach", "Baruch",
    "Letter of Jeremiah", "Prayer of Azariah", "Susanna", "Bel and the Dragon",
    "1 Maccabees", "2 Maccabees", "1 Esdras", "2 Esdras", "Prayer of Manasseh"
]

TRANSLATION_CODES = {
    # Modern copyrighted (kept for your reference)
    "NIV": {"label": "New International Version", "supports_apocrypha": False},
    "ESV": {"label": "English Standard Version", "supports_apocrypha": False},
    "EXB": {"label": "Expanded Bible", "supports_apocrypha": False},
    "NASB": {"label": "New American Standard Bible", "supports_apocrypha": False},
    "NLT": {"label": "New Living Translation", "supports_apocrypha": False},
    "CSB": {"label": "Christian Standard Bible", "supports_apocrypha": False},
    "NKJV": {"label": "New King James Version", "supports_apocrypha": False},
    "NRSV": {"label": "New Revised Standard Version", "supports_apocrypha": True},
    "RSVCE": {"label": "Revised Standard Version Catholic Edition", "supports_apocrypha": True},
    "CEB": {"label": "Common English Bible", "supports_apocrypha": True},
    "TLA": {"label": "Traducción en Lenguaje Actual (Spanish)", "supports_apocrypha": False},

    # --- PUBLIC DOMAIN TRANSLATIONS ---
    "KJV": {"label": "King James Version", "supports_apocrypha": True},
    "ASV": {"label": "American Standard Version (1901)", "supports_apocrypha": False},
    "ERV": {"label": "English Revised Version (1885)", "supports_apocrypha": False},
    "WEB": {"label": "World English Bible", "supports_apocrypha": False},
    "YLT": {"label": "Young's Literal Translation", "supports_apocrypha": False},
    "DBY": {"label": "Darby Translation", "supports_apocrypha": False},
    "JUB": {"label": "Jubilee Bible 2000", "supports_apocrypha": False},
    "DRC": {"label": "Douay-Rheims 1899 American Edition", "supports_apocrypha": True},
    "DRB": {"label": "Douay-Rheims Bible (Challoner)", "supports_apocrypha": True},  # Some use DRC, some DRB
    "RVA": {"label": "Reina-Valera Antigua (Spanish)", "supports_apocrypha": False},

    # Original language/public domain Greek/Hebrew
    "TR1550": {"label": "Textus Receptus 1550 (Greek)", "supports_apocrypha": False, "hebrew_greek": True},
    "SBLGNT": {"label": "SBL Greek New Testament", "supports_apocrypha": False, "hebrew_greek": True},
    "WLC": {"label": "Westminster Leningrad Codex (Hebrew)", "supports_apocrypha": False, "hebrew_greek": True},
    "LXX": {"label": "Septuagint (Brenton)", "supports_apocrypha": True, "hebrew_greek": True},
    "HHH": {"label": "Habrit Hakhadasha/Haderekh (Hebrew NT)", "supports_apocrypha": False, "hebrew_greek": True},
    # Keep your Geneva Bible entry for reference (may not be on BG in full):
    "GNV": {"label": "Geneva Bible", "supports_apocrypha": True}
}

def normalize_book_name(book):
    """Use spaces for BibleGateway passage search (no + sign)"""
    return book.strip()

class BibleGatewayFetcher:
    BASE_URL = "https://www.biblegateway.com/passage/"
    MAX_CHAPTERS = 150
    MAX_VERSES = 200

    def __init__(self, user_agent: str = None, delay_between_requests=1.5):
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        self.delay = delay_between_requests

    def _build_url(self, book, chapter=None, verse=None, translation=None):
        search = normalize_book_name(book)
        if chapter:
            search += f" {chapter}"
            if verse:
                search += f":{verse}"
        params = {
            "search": search,
            "version": translation or "NIV",
            "interface": "print"
        }
        param_str = "&".join([f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()])
        return f"{self.BASE_URL}?{param_str}"

    def _extract_structured(self, html, book=None, chapter=None):
        soup = BeautifulSoup(html, "html.parser")
        # Try both possible main divs (order: passage-content, then passage-text)
        content = soup.find("div", class_="passage-content") or soup.find("div", class_="passage-text")
        if not content:
            # Save HTML for debugging if not found!
            with open("last_failed_passage.html", "w", encoding="utf-8") as f:
                f.write(html)
            raise Exception("Could not find passage-content or passage-text block in HTML. Saved to last_failed_passage.html")
        
        items = []
        for elem in content.descendants:
            if isinstance(elem, Tag):
                # Heading
                if elem.name in ("h3", "h2") and elem.get_text(strip=True):
                    items.append({"type": "heading", "text": elem.get_text(strip=True)})
                # Section Headings
                elif "section-head" in elem.get("class", []):
                    items.append({"type": "section", "text": elem.get_text(strip=True)})
                # Verses (main)
                elif elem.name == "span" and "text" in elem.get("class", []):
                    verse_number = None
                    for cls in elem.get("class", []):
                        m = re.match(r'([1-3]?[A-Za-z]+(?:-[A-Za-z]+)*)(?:-(\d+))?(?:-(\d+))?', cls)
                        if m and m.group(3):
                            verse_number = int(m.group(3))
                            break
                    if not verse_number:
                        if elem.has_attr("data-verse"):
                            verse_number = int(elem["data-verse"])
                        else:
                            prev = elem.find_previous_sibling("sup", class_="versenum")
                            if prev and prev.get_text(strip=True).isdigit():
                                verse_number = int(prev.get_text(strip=True))
                    verse_dict = {
                        "type": "verse",
                        "book": book,
                        "chapter": chapter,
                        "number": verse_number,
                        "text": elem.get_text(separator=" ", strip=True)
                    }
                    items.append(verse_dict)
                # Footnotes
                elif elem.name == "span" and "footnote" in elem.get("class", []):
                    symbol = elem.get("data-symbol") or elem.get_text(strip=True)
                    text = ""
                    note = elem.find("div", class_="footnote-text")
                    if note:
                        text = note.get_text(separator=" ", strip=True)
                    else:
                        text = elem.get_text(separator=" ", strip=True)
                    items.append({
                        "type": "footnote",
                        "symbol": symbol,
                        "text": text
                    })
                elif elem.name == "p" and elem.get_text(strip=True):
                    items.append({"type": "paragraph", "text": elem.get_text(separator=" ", strip=True)})
                elif elem.name == "span" and "crossreference" in elem.get("class", []):
                    symbol = elem.get("data-symbol") or elem.get_text(strip=True)
                    text = elem.get_text(separator=" ", strip=True)
                    items.append({
                        "type": "crossref",
                        "symbol": symbol,
                        "text": text
                    })
        clean = []
        seen = set()
        for i in items:
            sig = (i.get("type"), i.get("text"), i.get("number"))
            if i["type"] == "verse":
                if not i["text"].strip() or i["text"].startswith("[") or i["number"] is None:
                    continue
            if sig not in seen:
                clean.append(i)
                seen.add(sig)
        return clean

    def fetch_verse(self, book, chapter, verse, translation="NIV"):
        url = self._build_url(book, chapter, verse, translation)
        html = self._get_page(url)
        items = self._extract_structured(html, book=book, chapter=chapter)
        return [item for item in items if item["type"] == "verse" and item.get("number") == int(verse)]

    def fetch_verse_range(self, book, chapter, verse_start, verse_end, translation="NIV"):
        url = self._build_url(book, chapter, f"{verse_start}-{verse_end}", translation)
        html = self._get_page(url)
        items = self._extract_structured(html, book=book, chapter=chapter)
        return [item for item in items if item["type"] == "verse" and verse_start <= item["number"] <= verse_end]

    def fetch_entire_chapter(self, book, chapter, translation="NIV"):
        url = self._build_url(book, chapter, translation=translation)
        html = self._get_page(url)
        return self._extract_structured(html, book=book, chapter=chapter)

    def fetch_entire_book(self, book, translation="NIV"):
        all_items = []
        consecutive_failures = 0
        for chapter in range(1, self.MAX_CHAPTERS+1):
            try:
                ch_items = self.fetch_entire_chapter(book, chapter, translation)
                verse_count = sum(1 for x in ch_items if x["type"] == "verse")
                if verse_count == 0:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        break
                else:
                    consecutive_failures = 0
                    all_items.extend(ch_items)
            except Exception as e:
                print(f"Failed to fetch {book} {chapter}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break
            time.sleep(self.delay)
        return all_items

    def _get_page(self, url):
        print("Fetching URL:", url)
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise Exception(f"Error fetching page: {url} (status {resp.status_code})")
        html = resp.text

        # --- Patch: auto-follow search result if not a direct passage ---
        soup = BeautifulSoup(html, "html.parser")
        passage_text = soup.find("div", class_="passage-content") or soup.find("div", class_="passage-text")
        if not passage_text:
            result_list = soup.find("div", class_="search-result-list")
            if result_list:
                first_link = result_list.find("a", href=True)
                if first_link:
                    next_url = "https://www.biblegateway.com" + first_link['href']
                    print("Auto-following search result:", next_url)
                    resp2 = requests.get(next_url, headers=self.headers)
                    if resp2.status_code == 200:
                        return resp2.text
                    else:
                        raise Exception(f"Error following search result: {next_url} (status {resp2.status_code})")
        return html
