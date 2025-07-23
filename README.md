# Scripture Scrapeway w/ GUI
Pulls full Bible Scripture in customizable quantities; utilizes a GUI with easy to use UI. Saves as JSON.

# BibleGateway Structured Scraper & GUI

A dark-mode, Firestore-ready Bible scraping tool and GUI for bulk or interactive passage retrieval from [BibleGateway.com](https://www.biblegateway.com/).  
**Auto-saves** JSON per book, supports entire Bible download, pause/continue/cancel, and structured output for data analysis or database import.

## Features

- **Dark Mode GUI** with color-coded output (headings, verses, footnotes, etc.)
- **Fetch single verse, verse range, chapter, book, or entire Bible**
- **Save as JSON** (Firestore-compatible) with each element tagged (type, verse, heading, etc.)
- **Download entire Bible** for any supported translation, with auto-save per book, pause/resume/cancel, and progress bar
- **Copy or export JSON** for further analysis or import
- **Open source** (MIT license), donation-friendly

## Usage

1. **Install Requirements**
    ```sh
    pip install requests beautifulsoup4
    ```

2. **Run the GUI**
    ```sh
    python bible_verse_gui.py
    ```

3. **Select** the passage, translation, and fetch mode. For bulk download, use the "Download Entire Bible" controls.

4. **Output** appears in the lower window.  
   Use "Copy JSON" or "Download JSON" for your data.  
   Entire Bible mode saves each book to the folder you specify.

## Notes & Disclaimers

- **This project is unaffiliated with BibleGateway.com.**  
  It simply fetches publicly available content for research, analysis, and private study.
- Please respect [BibleGateway's Terms of Use](https://www.biblegateway.com/legal/).  
  Do not use for abusive or commercial mass scraping.  
  This tool is designed for personal, educational, and non-abusive use only.
- All data and copyrights for translations belong to their respective publishers.
- Donations are for continued development and support of this software only.

## License

This project is licensed under the MIT License—see [LICENSE](LICENSE) for details.

## Acknowledgments

- [BibleGateway.com](https://www.biblegateway.com/) — For providing web access to Bible translations
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) — For HTML parsing
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — For GUI
- Parts of this project were assisted by OpenAI's GPT-4 (Code GPT).

---

### Want to support the project?
[Sponsor me on GitHub](https://github.com/sponsors/Hanson-2)

---

