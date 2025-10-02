#!/usr/bin/env python3
"""
Convert local kjv.json → Obsidian vault (one verse per note).

Now with:
- book-name normalization
- ordinal-prefixed book folders ("01 - Genesis" … "66 - Revelation")
- YAML per verse: book, chapter, verse, ordinal_verse, ref, translation, genre,
  word_count, topics: [], cross_references: [], grammar_tags: [], thematic_tags: []
- Clean split: grammar/form vs. themes/content
- No connectors/links in the body
"""

import json
import argparse
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

# ---------------- Canon & mappings ----------------

BOOKS_IN_ORDER = [
 "Genesis","Exodus","Leviticus","Numbers","Deuteronomy",
 "Joshua","Judges","Ruth","1 Samuel","2 Samuel","1 Kings","2 Kings",
 "1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther",
 "Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon",
 "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel",
 "Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk",
 "Zephaniah","Haggai","Zechariah","Malachi",
 "Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians",
 "Galatians","Ephesians","Philippians","Colossians","1 Thessalonians","2 Thessalonians",
 "1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter","2 Peter",
 "1 John","2 John","3 John","Jude","Revelation"
]
BOOK_TO_ORD = {b: i+1 for i, b in enumerate(BOOKS_IN_ORDER)}

BOOK_NAME_FIX = {
    "1Samuel":"1 Samuel","2Samuel":"2 Samuel",
    "1Kings":"1 Kings","2Kings":"2 Kings",
    "1Chronicles":"1 Chronicles","2Chronicles":"2 Chronicles",
    "1Corinthians":"1 Corinthians","2Corinthians":"2 Corinthians",
    "1Thessalonians":"1 Thessalonians","2Thessalonians":"2 Thessalonians",
    "1Timothy":"1 Timothy","2Timothy":"2 Timothy",
    "1Peter":"1 Peter","2Peter":"2 Peter",
    "1John":"1 John","2John":"2 John","3John":"3 John",
    "SongofSolomon":"Song of Solomon","SongofSongs":"Song of Solomon","Canticles":"Song of Solomon",
}

BOOK_GENRE = {
    "Genesis":"Law","Exodus":"Law","Leviticus":"Law","Numbers":"Law","Deuteronomy":"Law",
    "Joshua":"History","Judges":"History","Ruth":"History",
    "1 Samuel":"History","2 Samuel":"History","1 Kings":"History","2 Kings":"History",
    "1 Chronicles":"History","2 Chronicles":"History","Ezra":"History","Nehemiah":"History","Esther":"History",
    "Job":"Poetry/Wisdom","Psalms":"Poetry/Wisdom","Proverbs":"Poetry/Wisdom","Ecclesiastes":"Poetry/Wisdom","Song of Solomon":"Poetry/Wisdom",
    "Isaiah":"Major Prophet","Jeremiah":"Major Prophet","Lamentations":"Major Prophet","Ezekiel":"Major Prophet","Daniel":"Major Prophet",
    "Hosea":"Minor Prophet","Joel":"Minor Prophet","Amos":"Minor Prophet","Obadiah":"Minor Prophet","Jonah":"Minor Prophet","Micah":"Minor Prophet",
    "Nahum":"Minor Prophet","Habakkuk":"Minor Prophet","Zephaniah":"Minor Prophet","Haggai":"Minor Prophet","Zechariah":"Minor Prophet","Malachi":"Minor Prophet",
    "Matthew":"Gospel","Mark":"Gospel","Luke":"Gospel","John":"Gospel",
    "Acts":"History",
    "Romans":"Pauline Epistle","1 Corinthians":"Pauline Epistle","2 Corinthians":"Pauline Epistle",
    "Galatians":"Pauline Epistle","Ephesians":"Pauline Epistle","Philippians":"Pauline Epistle","Colossians":"Pauline Epistle",
    "1 Thessalonians":"Pauline Epistle","2 Thessalonians":"Pauline Epistle",
    "1 Timothy":"Pauline Epistle","2 Timothy":"Pauline Epistle","Titus":"Pauline Epistle","Philemon":"Pauline Epistle",
    "Hebrews":"General Epistle","James":"General Epistle","1 Peter":"General Epistle","2 Peter":"General Epistle",
    "1 John":"General Epistle","2 John":"General Epistle","3 John":"General Epistle","Jude":"General Epistle",
    "Revelation":"Apocalypse",
}

# ---------------- Theme dictionaries (all lowercase) ----------------

NAMES_OF_GOD = {
    "jehovah","yahweh","yhwh","lord","god","el","eloah","elohim","adonai","most high","almighty",
    "jehovah-jireh","jehovah jireh","yahweh-yireh","yahweh yireh",
    "jehovah-rapha","jehovah rapha","yahweh-rapha","yahweh rapha",
    "jehovah-nissi","jehovah nissi","yahweh-nissi","yahweh nissi",
    "jehovah-shalom","jehovah shalom","yahweh-shalom","yahweh shalom",
    "jehovah-raah","jehovah raah","yahweh-raah","yahweh raah",
    "jehovah-tsidkenu","jehovah tsidkenu","yahweh-tsidqenu","yahweh tsidqenu",
    "jehovah-shammah","jehovah shammah","yahweh-shammah","yahweh shammah",
    "lord of hosts","king of kings","lord of lords","ancient of days","the rock","i am","i am that i am"
}

PHYSICAL_WARFARE = {
    " war ", " war.", ", war","war, ","battle","battles","fight","fought","fighting","army","armies","hosts",
    "chariot","chariots","spear","spears","sword","swords","shield","shields",
    "captains","horse","horses","siege","besieged","slain","smote","smite","smitten","kill","killed"
}

SPIRITUAL_WARFARE = {
    "armor of god","whole armour of god","devil","devils","satan","tempter","temptation","stronghold","strongholds",
    "principalities","powers","rulers of the darkness","spiritual wickedness","fiery darts","resist","deliver us from evil"
}

ONE_ANOTHER_PHRASES = {
    "one another","each other","one to another","one toward another","members one of another"
}

# Christology
JESUS_TITLES = {
    "jesus","jesus christ","christ jesus","the christ","christ","messiah","immanuel","emmanuel","rabbi","teacher"
}
JESUS_SON_OF_GOD = {"son of god","only begotten son"}
JESUS_SON_OF_MAN = {"son of man"}
JESUS_LORD_PHRASES = {"lord jesus","our lord jesus","lord jesus christ"}
JESUS_LAMB_WORD = {"lamb of god"}

# Prayer & worship
THANKSGIVING_WORDS = {"give thanks","thanksgiving","thanks be","thank","thanked","thankful"}
PRAISE_WORDS = {"praise","praised","praiseth","sing","sang","sung","worship","bless the lord","bless the name"}
LAMENT_WORDS = {"woe","lament","tears","mourn","mourning","cry","cried","crying"}

# Covenant / promise
COVENANT_WORDS = {"covenant","everlasting covenant","my covenant","new covenant"}

# Blessing & benediction
BENEDICTION_WORDS = {
    "blessed is","blessed be","peace be","the lord bless thee","the lord make his face shine","the lord lift up"
}

# Ethical exhortations
NEG_COMMAND_PATTERNS = {"do not","be not","let not","thou shalt not"}
POS_COMMAND_PATTERNS = {"thou shalt","ye shall","you shall"}
FRUIT_WORKS_WORDS = {"fruit of the spirit","works of the flesh","good works","evil works"}

# Time / eschatology
TIME_MARKERS = {"in that day","at that time","for ever","forever","until","the last days","the latter days","day of the lord","time appointed","evening","morning","time","hour","days"}

# Adversary / demonic
ADVERSARY_TITLES = {"satan","devil","lucifer","beelzebub","belial","antichrist","the wicked one","the evil one","the adversary"}
ADVERSARY_EPITHETS = {"accuser","tempter","destroyer","deceiver","father of lies","murderer from the beginning",
                      "prince of this world","prince of the power of the air","god of this world","that wicked",
                      "man of sin","son of perdition","mystery of iniquity"}
ADVERSARY_METAPHORS = {"serpent","that old serpent","dragon","red dragon","roaring lion","leviathan","angel of light"}
ADVERSARY_NAMED_ENTITIES = {"abaddon","apollyon","legion"}
DEMONIC_ENTITIES = {"devils","unclean spirit","unclean spirits","evil spirit","evil spirits","familiar spirit","familiar spirits"}
DEMONIC_PHRASES = {"works of the devil","synagogue of satan","power of darkness","rulers of the darkness","doctrines of devils","possessed with a devil","cast out devils"}

LUCIFER_WORDS = (ADVERSARY_TITLES | ADVERSARY_EPITHETS | ADVERSARY_METAPHORS |
                 ADVERSARY_NAMED_ENTITIES | DEMONIC_ENTITIES | DEMONIC_PHRASES)

# --- Time / eschatology (split categories) ---

TIME_ESCHATOLOGY = {
    "in the last days","the last days","the latter days","in that day","in those days",
    "day of the lord","the time of the end","the end of days","time appointed","times and seasons",
    "a time times and an half","forty and two months","one thousand two hundred and threescore days",
    "shortly come to pass","the time is at hand","he that shall come will come",
    "from everlasting to everlasting","for ever and ever","the fullness of time",
}

TIME_UNITS = {
    "day","days","month","months","year","years","week","weeks","sabbath","sabbaths","jubilee"
}

TIME_PARTS_OF_DAY = {
    "morning","noon","evening","night","midnight","dawning of the day","break of day",
    "the third hour","the sixth hour","the ninth hour","the eleventh hour",
    "watch of the night","first watch","second watch","third watch","fourth watch"
}

TIME_SEASONS = {
    "winter","summer","harvest","seedtime","cold and heat",
    "former rain","latter rain","early rain","time of the latter rain"
}

TIME_FEASTS = {
    "passover","feast of unleavened bread","pentecost","feast of weeks","feast of trumpets",
    "day of atonement","feast of tabernacles","feast of booths","new moon","new moons","sabbath day"
}

TIME_PERIOD_PHRASES = {
    "at that time","at the time appointed","at the end of","in process of time",
    "after many days","after these things","before these days","from that day forward",
    "hereafter","henceforth","from this time forth","till the day","until the time","until the day",
    "for a season","for a time","for a long time","for a little while","not many days hence",
    "yet a little while","a little season"
}

TIME_MARKERS = (TIME_ESCHATOLOGY | TIME_UNITS | TIME_PARTS_OF_DAY |
                TIME_SEASONS | TIME_FEASTS | TIME_PERIOD_PHRASES)

# ---------------- Utilities ----------------

SAFE_FILENAME = re.compile(r'[^A-Za-z0-9 .:\-]')
WORD_TOKEN = re.compile(r"[A-Za-z0-9']+")

# --- WORD/PHRASE MATCHING HELPERS ---

WORD_RE = re.compile(r"[A-Za-z0-9']+")

def sanitize_filename(name: str) -> str:
    return SAFE_FILENAME.sub('', name).strip()

def fix_book_name(raw: str) -> str:
    raw = str(raw).strip()
    return BOOK_NAME_FIX.get(raw, raw)

def get_book_ordinal(book: str) -> int:
    if book not in BOOK_TO_ORD:
        raise ValueError(f"Unknown canonical book name: {book}")
    return BOOK_TO_ORD[book]

def ord_folder_name(book: str, pad: int) -> str:
    n = get_book_ordinal(book)
    num = f"{n:0{pad}d}" if pad and pad > 0 else str(n)
    return f"{num} - {book}"

def word_count(text: str) -> int:
    return len(WORD_TOKEN.findall(text))

def dedup_preserve(seq: List[str]) -> List[str]:
    seen = set(); out: List[str] = []
    for s in seq:
        if s not in seen:
            out.append(s); seen.add(s)
    return out

# ---------------- Tagging (SPLIT) ----------------

def detect_grammar_tags(text: str, book: str) -> List[str]:
    """Form/structure only: punctuation, discourse openers, logical relations, mood."""
    t = text.strip()
    tl = t.lower()
    tags: List[str] = []

    # punctuation
    if t.endswith("?"): tags.append("question")
    if t.endswith("!"): tags.append("exclamation")
    if any(q in t for q in ['"', "“", "”", "‘", "’"]): tags.append("dialogue")
    if t.count(";") >= 2: tags.append("semicolon-heavy")

    # openers / discourse cues
    words = tl.split(); first = words[0] if words else ""
    CONTRAST_OPENERS = {"but","however","yet","nevertheless","though","still","rather"}
    INFERENCE_OPENERS = {"therefore","wherefore","so","then"}
    CONJUNCTIVE_OPENERS = {"and"}
    if first in CONTRAST_OPENERS: tags.append("contrast-opener")
    if first in INFERENCE_OPENERS: tags.append("inference-opener")
    if first in CONJUNCTIVE_OPENERS: tags.append("conjunctive-opener")

    # grammatical mood / polarity
    if any(x in tl for x in (" not ","neither"," nor ","without"," no "," never ")):
        tags.append("negation")

    # contrast markers anywhere
    if any(x in tl for x in (" but "," but,","but, ","yet","however","nevertheless","though")):
        tags.append("contrast")

    # conditional (explicit + rhetorical)
    conditional = False
    if "if" in tl: conditional = True
    if any(x in tl for x in ("unless","except","provided that","in case","whether","lest","though")):
        conditional = True
    if any(x in tl for x in ("what if","think ye","think you","shall we","should we","would we","would you","could we","suppose")):
        conditional = True
    if t.endswith("?") and any(x in tl for x in ("think","suppose","consider","reckon")):
        conditional = True
    if conditional: tags.append("conditional")

    # logical relation
    if any(x in tl for x in ("therefore","for this cause","so that")):
        tags.append("cause-effect")

    # formulaic closings (still grammar-ish)
    if any(x in tl for x in ("grace be unto you","grace be to you","grace and peace"," amen")):
        tags.append("greeting/closing")

    # genealogical construction (structural pattern)
    if "begat" in tl or "son of" in tl or "daughter of" in tl:
        tags.append("genealogy-structure")

    return dedup_preserve(tags)

def detect_thematic_tags(text: str, book: str) -> List[str]:
    tl = text.strip().lower()
    tags: List[str] = []

    # core themes
    if any(name in tl for name in NAMES_OF_GOD): tags.append("names-of-god")
    if any(w in tl for w in PHYSICAL_WARFARE): tags.append("warfare")
    if any(w in tl for w in SPIRITUAL_WARFARE): tags.append("warfare")
    if any(phrase in tl for phrase in ONE_ANOTHER_PHRASES): tags.append("one-another")

    # Christology
    if any(p in tl for p in JESUS_LORD_PHRASES) or "jesus" in tl: tags.append("jesus")
    if any(p in tl for p in JESUS_TITLES): tags.append("jesus-title"); tags.append("jesus")
    if any(p in tl for p in JESUS_SON_OF_GOD): tags.append("son-of-god"); tags.append("jesus")
    if any(p in tl for p in JESUS_SON_OF_MAN): tags.append("son-of-man"); tags.append("jesus")
    if any(p in tl for p in JESUS_LAMB_WORD): tags.append("lamb-of-god"); tags.append("jesus")

    # adversary / demonic
    if any(w in tl for w in ADVERSARY_TITLES):        tags.append("adversary-title")
    if any(w in tl for w in ADVERSARY_EPITHETS):      tags.append("adversary-epithet")
    if any(w in tl for w in ADVERSARY_METAPHORS):     tags.append("adversary-metaphor")
    if any(w in tl for w in ADVERSARY_NAMED_ENTITIES):tags.append("adversary-named")
    if any(w in tl for w in DEMONIC_ENTITIES):        tags.append("demonic-entities")
    if any(w in tl for w in DEMONIC_PHRASES):         tags.append("demonic-phrases")
    if any(w in tl for w in LUCIFER_WORDS):           tags.append("adversary")

    # prayer & worship
    if any(w in tl for w in THANKSGIVING_WORDS):      tags.append("thanksgiving")
    if any(w in tl for w in PRAISE_WORDS):            tags.append("praise-worship")
    if any(w in tl for w in LAMENT_WORDS):            tags.append("lament")

    # covenant / promise
    if any(w in tl for w in COVENANT_WORDS):          tags.append("covenant")

    # blessing & benediction
    if any(w in tl for w in BENEDICTION_WORDS):       tags.append("benediction")

    # ethics
    if any(tl.startswith(p) for p in NEG_COMMAND_PATTERNS):
        tags.append("negative-command")
    elif any(tl.startswith(p) for p in POS_COMMAND_PATTERNS):
        tags.append("positive-command")

    # time / eschatology
    if any(w in tl for w in TIME_ESCHATOLOGY):   tags.append("time-eschatology")
    if any(w in tl for w in TIME_UNITS):         tags.append("time-units")
    if any(w in tl for w in TIME_PARTS_OF_DAY):  tags.append("time-parts-of-day")
    if any(w in tl for w in TIME_SEASONS):       tags.append("time-seasons")
    if any(w in tl for w in TIME_FEASTS):        tags.append("time-feasts")
    if any(w in tl for w in TIME_PERIOD_PHRASES):tags.append("time-period")
    if any(w in tl for w in TIME_MARKERS):       tags.append("time")

    return dedup_preserve(tags)

# ---------------- Writer ----------------

def write_markdown(entry: Dict[str, Any], out_root: Path, translation="KJV",
                   force=False, verbose=False, pad=2) -> bool:
    for key in ("book","chapter","verse","text","ordinal_verse"):
        if key not in entry:
            if verbose:
                print(f"[warn] Missing key {key!r} in entry: {entry}")
            return False

    book = fix_book_name(entry["book"])
    booktag = book.replace(" ", "-")
    if book not in BOOK_TO_ORD:
        if verbose:
            print(f"[warn] Book not recognized: {entry['book']} (normalized: {book})")
        return False

    try:
        chapter = int(entry["chapter"])
        verse = int(entry["verse"])
        ordinal = int(entry["ordinal_verse"])
    except Exception:
        if verbose:
            print(f"[warn] Non-integer field for entry: {entry}")
        return False

    text = str(entry["text"]).strip()
    if not text:
        if verbose:
            print(f"[warn] Empty verse text for {book} {chapter}:{verse}")
        return False

    ref = f"{book} {chapter}:{verse}"
    genre = BOOK_GENRE.get(book, "Unknown")
    wc = word_count(text)

    grammar_tags = detect_grammar_tags(text, book)
    thematic_tags = detect_thematic_tags(text, book)

    # Top-level folder: "<ordinal> - <Book>"
    book_dir = out_root / ord_folder_name(book, pad)
    book_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(f"{book} {chapter}.{verse}.md")
    path = book_dir / filename
    if path.exists() and not force:
        if verbose:
            print(f"[skip] Exists: {book}")
        return False

    content = f"""---
book: "{book}"
chapter: {chapter}
verse: {verse}
ordinal_verse: {ordinal}
ref: "{ref}"
translation: "{translation}"
genre: "{genre}"
word_count: {wc}
topics: []
cross_references: []
grammar_tags: [{", ".join(grammar_tags)}]
thematic_tags: [{", ".join(thematic_tags)}]
tags: ["Bible","KJV","{booktag}"]
---
{text}
"""
    path.write_text(content, encoding="utf-8")
    if verbose:
        print(f"[write] {path}")
    return True

# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", required=True, help="Path to kjv.json")
    ap.add_argument("--out", required=True, help="Output folder (e.g. /path/to/Vault/Bible)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files")
    ap.add_argument("--verbose", action="store_true", help="Print diagnostics")
    ap.add_argument("--pad", type=int, default=2, help="Zero-pad width for ordinals (0 = no padding)")
    args = ap.parse_args()

    infile = Path(args.infile).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"[info] Reading: {infile}")
        print(f"[info] Output : {out_root}")
        print(f"[info] Ordinal padding: {args.pad}")

    if not infile.exists():
        print(f"[error] Input file not found: {infile}", file=sys.stderr)
        sys.exit(2)

    raw = infile.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[error] JSON parse error: {e}", file=sys.stderr)
        sys.exit(3)

    if not isinstance(data, list):
        print(f"[error] Expected a top-level list in {infile}", file=sys.stderr)
        sys.exit(4)

    written = 0
    skipped = 0
    errors = 0
    for i, entry in enumerate(data):
        try:
            ok = write_markdown(entry, out_root, force=args.force, verbose=args.verbose, pad=args.pad)
            if ok: written += 1
            else: skipped += 1
        except Exception as e:
            errors += 1
            if args.verbose:
                print(f"[error] Entry {i} failed: {e}")

        if args.verbose and (i + 1) % 2000 == 0:
            print(f"[info] Progress: {i + 1} entries processed...")

    print(f"[done] Written: {written} | Skipped: {skipped} | Errors: {errors} | Output: {out_root}")

if __name__ == "__main__":
    main()
