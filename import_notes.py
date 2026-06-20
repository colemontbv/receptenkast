"""
Importeert geëxporteerde Apple Notities (.txt bestanden, één per recept) in de
receptendatabase. De volledige tekst van elke notitie komt in het notities-veld
terecht — ingrediënten/stappen worden NIET automatisch herkend, want vrije tekst
uit Notities is daarvoor te ongestructureerd om betrouwbaar te splitsen.

Elk geïmporteerd recept krijgt de tag "te-verwerken" zodat je ze makkelijk kan
terugvinden in de app en via het bewerk-scherm kan omzetten naar een
ingrediënten-/stappenlijst (kopiëren uit het notities-veld gaat snel).

Gebruik:
    python import_notes.py /pad/naar/geëxporteerde/map
"""

import sys
from pathlib import Path

from database import get_db, init_db


def main():
    if len(sys.argv) != 2:
        print("Gebruik: python import_notes.py /pad/naar/geëxporteerde/map")
        sys.exit(1)

    folder = Path(sys.argv[1]).expanduser()
    if not folder.is_dir():
        print(f"Map niet gevonden: {folder}")
        sys.exit(1)

    txt_files = sorted(folder.glob("*.txt"))
    if not txt_files:
        print(f"Geen .txt bestanden gevonden in {folder}")
        sys.exit(1)

    init_db()
    db = get_db()
    imported = 0

    for f in txt_files:
        title = f.stem
        body = f.read_text(encoding="utf-8", errors="replace").strip()

        existing = db.execute("SELECT id FROM recipes WHERE title = ?", (title,)).fetchone()
        if existing:
            print(f"Overslaan (bestaat al): {title}")
            continue

        db.execute(
            "INSERT INTO recipes (title, servings, tags, notes) VALUES (?, ?, ?, ?)",
            (title, 4, "te-verwerken", body),
        )
        imported += 1
        print(f"Geïmporteerd: {title}")

    db.commit()
    db.close()
    print(f"\nKlaar — {imported} van de {len(txt_files)} recepten geïmporteerd.")


if __name__ == "__main__":
    main()
