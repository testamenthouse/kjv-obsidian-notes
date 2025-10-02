# KJV → Obsidian (One Verse per Note)

This project converts a JSON copy of the King James Bible into an Obsidian vault where **each verse is its own Markdown note**.  
The result: a neatly organized, tag-ready, vault.

---

## Features

- Atomic notes – one verse per file.  
- Ordered folders – `01 - Genesis` → `66 - Revelation`.  
- Rich YAML frontmatter per verse:
  ```yaml
  book: "Genesis"
  chapter: 1
  verse: 1
  ordinal_verse: 1
  ref: "Genesis 1:1"
  translation: "KJV"
  genre: ""
  word_count: 10
  topics: []
  cross_references: []
  grammar_tags: []
  thematic_tags: []
  ```

---

## Quick Start

1. Clone the repo
   ```bash
   git clone https://github.com/testamenthouse/kjv-obsidian-notes.git
   cd kjv-obsidian-notes
   ```

2. Run the converter
   ```bash
   # Check available flags
   python3 src/kjv_to_obsidian.py --help

   # Example run
   python3 src/kjv_to_obsidian.py --input /path/to/kjv.json --out ./notes-output
   ```

4. Open in Obsidian  
   - Open the generated `notes` folder as a new vault.  
   - (Optional) Install the **Dataview plugin** to query by tags like `topics`, `grammar_tags`, etc.

---

## Project Structure

```
src/                  # Converter script(s)
notes/                # Sample or prebuilt output
README.md
LICENSE               # Apache-2.0
```

---

## Contributing

PRs welcome!  
Ideas for improvement:
- More metadata enrichment  
- Cross-reference automation  
- Additional export formats  

---

## License

Licensed under the Apache-2.0 License.  
