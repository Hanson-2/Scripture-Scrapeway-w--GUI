import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import os
import time
from bible_verse_fetcher import BibleGatewayFetcher, CANONICAL_BOOKS, DEUTERO_BOOKS, TRANSLATION_CODES

BG_COLOR = "#232323"
FG_COLOR = "#ffffff"
HEADING_COLOR = "#bb2222"
VERSE_COLOR = "#ee4455"
FOOTNOTE_COLOR = "#b677bb"
CROSSREF_COLOR = "#77aabb"
PARAGRAPH_COLOR = "#cccccc"
ERROR_COLOR = "#ff4444"
BUTTON_BG = "#1a1a1a"
BUTTON_FG = "#ee4455"
FONT = ("Consolas", 11)

def format_item(item):
    if item["type"] == "heading":
        return f'[HEADING] {item["text"]}'
    elif item["type"] == "section":
        return f'[SECTION] {item["text"]}'
    elif item["type"] == "verse":
        return f'[VERSE {item.get("number", "?")}] {item["text"]}'
    elif item["type"] == "footnote":
        return f'[FOOTNOTE {item.get("symbol", "")}] {item["text"]}'
    elif item["type"] == "crossref":
        return f'[CROSSREF {item.get("symbol", "")}] {item["text"]}'
    elif item["type"] == "paragraph":
        return f'[PARAGRAPH] {item["text"]}'
    else:
        return f'[{item["type"].upper()}] {item.get("text","")}'

class BibleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BibleGateway Fetcher - Unified Edition")
        self.root.configure(bg=BG_COLOR)
        self.fetcher = BibleGatewayFetcher()
        self.result_data = None

        # --- Interactive Fetch Controls ---
        top_frame = tk.LabelFrame(root, text="Interactive Passage/Range/Chapter/Book Fetch", bg=BG_COLOR, fg=HEADING_COLOR, font=(FONT[0], FONT[1]+1, "bold"))
        top_frame.pack(fill=tk.X, padx=12, pady=(10, 4))

        # Book
        tk.Label(top_frame, text="Book:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=0, sticky="w")
        self.book_var = tk.StringVar(value="Genesis")
        self.book_box = ttk.Combobox(top_frame, textvariable=self.book_var, values=CANONICAL_BOOKS+DEUTERO_BOOKS, font=FONT, width=18, state="readonly")
        self.book_box.grid(row=0, column=1, padx=4)

        # Chapter
        tk.Label(top_frame, text="Chapter:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=2)
        self.chapter_var = tk.IntVar(value=1)
        tk.Spinbox(top_frame, from_=1, to=200, textvariable=self.chapter_var, font=FONT, width=5, bg=BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR).grid(row=0, column=3, padx=4)

        # Verse(s)
        tk.Label(top_frame, text="Verse:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=4)
        self.verse_var = tk.IntVar(value=1)
        tk.Spinbox(top_frame, from_=1, to=200, textvariable=self.verse_var, font=FONT, width=5, bg=BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR).grid(row=0, column=5, padx=4)
        tk.Label(top_frame, text="to", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=6)
        self.verse_end_var = tk.IntVar(value=1)
        tk.Spinbox(top_frame, from_=1, to=200, textvariable=self.verse_end_var, font=FONT, width=5, bg=BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR).grid(row=0, column=7, padx=4)

        # Translation
        tk.Label(top_frame, text="Translation:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=8)
        self.translation_var = tk.StringVar(value="KJV")
        self.translation_box = ttk.Combobox(top_frame, textvariable=self.translation_var, values=list(TRANSLATION_CODES.keys()), font=FONT, width=10, state="readonly")
        self.translation_box.grid(row=0, column=9, padx=4)
        self.translation_box.bind('<<ComboboxSelected>>', self.update_apocrypha_state)

        # Fetch Mode
        self.mode_var = tk.StringVar(value="verse")
        modes = [("Single Verse", "verse"), ("Verse Range", "range"), ("Full Chapter", "chapter"), ("Full Book", "book")]
        for idx, (text, val) in enumerate(modes):
            tk.Radiobutton(top_frame, text=text, variable=self.mode_var, value=val, bg=BG_COLOR, fg=BUTTON_FG,
                           selectcolor=BG_COLOR, font=FONT, activeforeground=HEADING_COLOR, activebackground=BG_COLOR).grid(row=1, column=idx, pady=(5,2), sticky="w")

        # Fetch Button
        tk.Button(top_frame, text="Fetch", font=FONT, bg=BUTTON_BG, fg=BUTTON_FG, activebackground=HEADING_COLOR, command=self.start_fetch).grid(row=1, column=5, padx=10, pady=4, sticky="w")

        # Copy/Download JSON Buttons
        tk.Button(top_frame, text="Copy JSON", font=FONT, bg=BUTTON_BG, fg=BUTTON_FG, command=self.copy_json).grid(row=1, column=6, padx=6)
        tk.Button(top_frame, text="Download JSON", font=FONT, bg=BUTTON_BG, fg=BUTTON_FG, command=self.save_json).grid(row=1, column=7, padx=6)

        # --- Divider ---
        tk.Label(root, text=" ", bg=BG_COLOR).pack(pady=2)

        # --- Batch Download Controls ---
        batch_frame = tk.LabelFrame(root, text="Batch: Multi-Book/Apocrypha Download", bg=BG_COLOR, fg=HEADING_COLOR, font=(FONT[0], FONT[1]+1, "bold"))
        batch_frame.pack(fill=tk.X, padx=12, pady=(0, 0))

        # Canonical Books Multi-Select
        tk.Label(batch_frame, text="Books:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=0, sticky="nw")
        self.canon_books_lb = tk.Listbox(batch_frame, selectmode=tk.MULTIPLE, height=10, width=19, exportselection=0,
                                         bg="#181818", fg=FG_COLOR, font=FONT)
        for book in CANONICAL_BOOKS:
            self.canon_books_lb.insert(tk.END, book)
        self.canon_books_lb.grid(row=1, column=0, rowspan=6, sticky="ns", pady=4)

        # Deuterocanonical Books Multi-Select (separate)
        tk.Label(batch_frame, text="Apocrypha:", bg=BG_COLOR, fg=HEADING_COLOR, font=FONT).grid(row=0, column=1, sticky="nw")
        self.deutero_books_lb = tk.Listbox(batch_frame, selectmode=tk.MULTIPLE, height=10, width=21, exportselection=0,
                                           bg="#181818", fg="#ffaaff", font=FONT)
        for book in DEUTERO_BOOKS:
            self.deutero_books_lb.insert(tk.END, book)
        self.deutero_books_lb.grid(row=1, column=1, rowspan=6, sticky="ns", pady=4)

        # Translation Combo (batch)
        tk.Label(batch_frame, text="Translation:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=2, sticky="w", padx=(12,0))
        self.batch_translation = tk.StringVar(value="KJV")
        self.batch_translation_box = ttk.Combobox(batch_frame, textvariable=self.batch_translation, values=list(TRANSLATION_CODES.keys()), font=FONT, width=10, state="readonly")
        self.batch_translation_box.grid(row=0, column=3, sticky="w", padx=(2,0))
        self.batch_translation_box.bind('<<ComboboxSelected>>', self.update_apocrypha_state)

        # Save Folder
        tk.Label(batch_frame, text="Save to:", bg=BG_COLOR, fg=FG_COLOR, font=FONT).grid(row=0, column=4, sticky="e", padx=(15,0))
        self.save_folder = tk.StringVar(value=os.getcwd())
        tk.Entry(batch_frame, textvariable=self.save_folder, font=FONT, width=24, bg="#181818", fg="#e6e6e6", bd=1).grid(row=0, column=5, padx=4)
        tk.Button(batch_frame, text="Browse", font=FONT, bg=BUTTON_BG, fg=BUTTON_FG, command=self.pick_folder).grid(row=0, column=6, padx=4)

        # Batch Download Controls
        self.download_btn = tk.Button(batch_frame, text="Download Selected Books", font=FONT, bg=BUTTON_BG, fg=BUTTON_FG, command=self.start_batch)
        self.download_btn.grid(row=1, column=4, columnspan=2, padx=2, pady=(4,0))
        self.pause_btn = tk.Button(batch_frame, text="Pause", font=FONT, bg=BUTTON_BG, fg="#FFD700", command=self.pause_batch, state=tk.DISABLED)
        self.pause_btn.grid(row=2, column=4, padx=2)
        self.continue_btn = tk.Button(batch_frame, text="Continue", font=FONT, bg=BUTTON_BG, fg="#9fff9f", command=self.continue_batch, state=tk.DISABLED)
        self.continue_btn.grid(row=2, column=5, padx=2)
        self.cancel_btn = tk.Button(batch_frame, text="Cancel", font=FONT, bg=BUTTON_BG, fg=ERROR_COLOR, command=self.cancel_batch, state=tk.DISABLED)
        self.cancel_btn.grid(row=2, column=6, padx=2)

        # Progress Bar and Status
        self.progress = ttk.Progressbar(batch_frame, orient="horizontal", length=340, mode="determinate")
        self.progress.grid(row=3, column=4, columnspan=3, pady=(6,0), sticky="ew")
        self.status_label = tk.Label(batch_frame, text="Ready.", bg=BG_COLOR, fg=PARAGRAPH_COLOR, font=FONT, anchor="w")
        self.status_label.grid(row=4, column=4, columnspan=3, sticky="w")

        # --- Scrolled Text Output Widget ---
        self.text = scrolledtext.ScrolledText(root, font=FONT, bg=BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR,
                                              width=110, height=22, wrap=tk.WORD, borderwidth=2, relief=tk.GROOVE)
        self.text.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.text.tag_configure("heading", foreground=HEADING_COLOR, font=(FONT[0], FONT[1]+2, "bold"))
        self.text.tag_configure("section", foreground=HEADING_COLOR, font=(FONT[0], FONT[1]+1, "italic"))
        self.text.tag_configure("verse", foreground=VERSE_COLOR)
        self.text.tag_configure("footnote", foreground=FOOTNOTE_COLOR)
        self.text.tag_configure("crossref", foreground=CROSSREF_COLOR)
        self.text.tag_configure("paragraph", foreground=PARAGRAPH_COLOR)
        self.text.tag_configure("error", foreground=ERROR_COLOR, font=(FONT[0], FONT[1]+1, "bold"))
        self.text.tag_configure("default", foreground=FG_COLOR)

        # --- Batch State
        self.batch_thread = None
        self.batch_paused = threading.Event()
        self.batch_cancel = threading.Event()

        self.update_apocrypha_state()

    def pick_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_folder.get() or os.getcwd())
        if folder:
            self.save_folder.set(folder)

    def update_apocrypha_state(self, event=None):
        # For both single and batch modes
        tr_code = self.translation_var.get()
        tr_batch = self.batch_translation.get()
        for lb in [self.deutero_books_lb]:
            state = tk.NORMAL if TRANSLATION_CODES.get(tr_batch or tr_code, {}).get("supports_apocrypha", False) else tk.DISABLED
            for i in range(lb.size()):
                lb.itemconfig(i, fg="#ffaaff" if state == tk.NORMAL else "#444444")
            if not state:
                lb.selection_clear(0, tk.END)
        # Also, if single-fetch is set to a deuterocanonical book, switch translation if needed
        single_book = self.book_var.get()
        if single_book in DEUTERO_BOOKS and not TRANSLATION_CODES.get(tr_code, {}).get("supports_apocrypha", False):
            # Switch to a translation that supports apocrypha
            for k, v in TRANSLATION_CODES.items():
                if v.get("supports_apocrypha"):
                    self.translation_var.set(k)
                    break

    # --- Interactive Fetch Methods ---
    def start_fetch(self):
        threading.Thread(target=self.do_fetch, daemon=True).start()

    def do_fetch(self):
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, "Fetching...", "section")
        self.text.update()
        try:
            book = self.book_var.get()
            chapter = int(self.chapter_var.get())
            verse = int(self.verse_var.get())
            verse_end = int(self.verse_end_var.get())
            translation = self.translation_var.get()
            mode = self.mode_var.get()
            if mode == "verse":
                items = self.fetcher.fetch_verse(book, chapter, verse, translation)
            elif mode == "range":
                items = self.fetcher.fetch_verse_range(book, chapter, verse, verse_end, translation)
            elif mode == "chapter":
                items = self.fetcher.fetch_entire_chapter(book, chapter, translation)
            elif mode == "book":
                items = self.fetcher.fetch_entire_book(book, translation)
            else:
                raise Exception("Unknown fetch mode")
            self.result_data = items
            self.display_result(items)
        except Exception as e:
            self.result_data = None
            self.text.delete(1.0, tk.END)
            self.text.insert(tk.END, f"Error: {str(e)}", "error")

    def display_result(self, items):
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        if not items:
            self.text.insert(tk.END, "No results found.", "error")
            return
        for item in items:
            out = format_item(item) + "\n"
            self.text.insert(tk.END, out, item["type"] if self.text.tag_cget(item["type"], "foreground") else "default")
        self.text.see(tk.END)

    def copy_json(self):
        if not self.result_data:
            messagebox.showwarning("No Data", "Nothing to copy!")
            return
        data = json.dumps(self.result_data, ensure_ascii=False, indent=2)
        self.root.clipboard_clear()
        self.root.clipboard_append(data)
        messagebox.showinfo("Copied", "JSON copied to clipboard!")

    def save_json(self):
        if not self.result_data:
            messagebox.showwarning("No Data", "Nothing to save!")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
        if not fname:
            return
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(self.result_data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Saved", f"JSON saved to {fname}")

    # --- Batch Download Methods ---
    def start_batch(self):
        if self.batch_thread and self.batch_thread.is_alive():
            messagebox.showwarning("Already Running", "Batch is already running.")
            return
        canon_idx = self.canon_books_lb.curselection()
        deutero_idx = self.deutero_books_lb.curselection()
        books = [self.canon_books_lb.get(i) for i in canon_idx]
        if TRANSLATION_CODES.get(self.batch_translation.get(), {}).get("supports_apocrypha", False):
            books += [self.deutero_books_lb.get(i) for i in deutero_idx]
        if not books:
            messagebox.showwarning("No Books", "Select at least one book.")
            return
        self.download_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.continue_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress["value"] = 0
        self.progress["maximum"] = len(books)
        self.status_label.config(text="Starting batch…")
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, f"Batch started...\n", "section")
        self.batch_paused.clear()
        self.batch_cancel.clear()
        save_folder = self.save_folder.get() or os.getcwd()
        translation = self.batch_translation.get()
        self.batch_thread = threading.Thread(
            target=self.do_batch_download,
            args=(books, save_folder, translation),
            daemon=True
        )
        self.batch_thread.start()

    def pause_batch(self):
        self.batch_paused.set()
        self.pause_btn.config(state=tk.DISABLED)
        self.continue_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Paused.")

    def continue_batch(self):
        self.batch_paused.clear()
        self.pause_btn.config(state=tk.NORMAL)
        self.continue_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Continuing…")


    def cancel_batch(self):
        self.batch_cancel.set()
        self.status_label.config(text="Canceling…")
        self.pause_btn.config(state=tk.DISABLED)
        self.continue_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        self.download_btn.config(state=tk.NORMAL)

    def do_batch_download(self, books, save_folder, translation):
        total = len(books)
        self.progress["maximum"] = total
        for idx, book in enumerate(books):
            while self.batch_paused.is_set():
                self.status_label.config(text=f"Paused on {book} ({idx+1}/{total})")
                time.sleep(0.25)
                if self.batch_cancel.is_set():
                    self.status_label.config(text="Batch canceled.")
                    return
            if self.batch_cancel.is_set():
                self.status_label.config(text="Batch canceled.")
                break
            self.progress["value"] = idx
            self.status_label.config(text=f"Fetching: {book} ({idx+1}/{total})")
            self.text.insert(tk.END, f"Fetching {book} ({translation})...\n", "section")
            self.text.see(tk.END)
            self.text.update()
            try:
                items = self.fetcher.fetch_entire_book(book, translation)
                fname = os.path.join(save_folder, f"{book.replace(' ','_')}_{translation}.json")
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                self.text.insert(tk.END, f"Saved {fname}\n", "paragraph")
            except Exception as e:
                self.text.insert(tk.END, f"Failed to fetch/save {book}: {str(e)}\n", "error")
            self.progress["value"] = idx+1
            self.text.see(tk.END)
            self.text.update()
            self.status_label.config(text=f"Completed: {book} ({idx+1}/{total})")
            time.sleep(0.5)
        self.status_label.config(text="Batch done." if not self.batch_cancel.is_set() else "Batch canceled.")
        self.download_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.continue_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress["value"] = total

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=BG_COLOR, foreground=FG_COLOR)
    app = BibleGUI(root)
    root.mainloop()
