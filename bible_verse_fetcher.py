import requests
from bs4 import BeautifulSoup, Tag
import re
import time

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
        search = book
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

    def _get_page(self, url):
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise Exception(f"Error fetching page: {url} (status {resp.status_code})")
        return resp.text

    def _extract_structured(self, html, book=None, chapter=None):
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", class_="passage-text")
        if not content:
            content = soup.find("div", class_="passage-content")
        if not content:
            raise Exception("Could not find passage-text or passage-content block in HTML.")

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
                    # Extract verse number from class if available (e.g., Gen-1-1)
                    verse_number = None
                    for cls in elem.get("class", []):
                        m = re.match(r'([A-Za-z]+)-(\d+)-(\d+)', cls)
                        if m:
                            verse_number = int(m.group(3))
                            break
                    if not verse_number:
                        # Fallback: try data-verse or sibling sup
                        if elem.has_attr("data-verse"):
                            verse_number = int(elem["data-verse"])
                        else:
                            # Search for preceding sup.versenum
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
                # Verse number (standalone, usually already handled)
                elif elem.name == "sup" and "versenum" in elem.get("class", []):
                    # Already handled above for most cases; skip here
                    continue
                # Footnotes
                elif elem.name == "span" and "footnote" in elem.get("class", []):
                    symbol = elem.get("data-symbol") or elem.get_text(strip=True)
                    text = ""
                    note = elem.find("div", class_="footnote-text")
                    if note:
                        text = note.get_text(separator=" ", strip=True)
                    else:
                        # Sometimes inline footnotes are just text after symbol
                        text = elem.get_text(separator=" ", strip=True)
                    items.append({
                        "type": "footnote",
                        "symbol": symbol,
                        "text": text
                    })
                # Paragraph (used for intros, summaries, etc.)
                elif elem.name == "p" and elem.get_text(strip=True):
                    items.append({"type": "paragraph", "text": elem.get_text(separator=" ", strip=True)})
                # Crossrefs (often 'crossreference' class or similar)
                elif elem.name == "span" and "crossreference" in elem.get("class", []):
                    symbol = elem.get("data-symbol") or elem.get_text(strip=True)
                    text = elem.get_text(separator=" ", strip=True)
                    items.append({
                        "type": "crossref",
                        "symbol": symbol,
                        "text": text
                    })
        # Remove empty or duplicate items
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
        # Return only the verse of interest, but preserve context
        context_items = []
        for item in items:
            if item["type"] == "verse" and item.get("number") == int(verse):
                context_items.append(item)
        return context_items

    def fetch_verse_range(self, book, chapter, verse_start, verse_end, translation="NIV"):
        url = self._build_url(book, chapter, f"{verse_start}-{verse_end}", translation)
        html = self._get_page(url)
        items = self._extract_structured(html, book=book, chapter=chapter)
        context_items = []
        for item in items:
            if item["type"] == "verse" and item.get("number") is not None:
                if verse_start <= item["number"] <= verse_end:
                    context_items.append(item)
            elif item["type"] != "verse":
                context_items.append(item)
        return context_items

    def fetch_entire_chapter(self, book, chapter, translation="NIV"):
        url = self._build_url(book, chapter, translation=translation)
        html = self._get_page(url)
        items = self._extract_structured(html, book=book, chapter=chapter)
        return items

    def fetch_entire_book(self, book, translation="NIV"):
        # Try to get number of chapters using a static lookup or implement a book:chapters dict
        # For now, attempt chapters up to MAX_CHAPTERS, stop after 3 consecutive empty chapters
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

# Example usage:
if __name__ == "__main__":
    fetcher = BibleGatewayFetcher()
    # Fetch Genesis 1:1
    verse = fetcher.fetch_verse("Genesis", 1, 1, "EXB")
    print(verse)

    # Fetch Genesis 1:1-5
    verses = fetcher.fetch_verse_range("Genesis", 1, 1, 5, "EXB")
    print(verses)

    # Fetch all of Genesis 1
    chapter = fetcher.fetch_entire_chapter("Genesis", 1, "EXB")
    print(chapter)
