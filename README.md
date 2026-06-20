# Receptenkast

Een lichte, zelf-gehoste receptenapp: zoeken op titel/ingrediënt, tags, porties
schalen, en een foto per recept. Draait lokaal met Flask + SQLite — geen
externe diensten nodig.

## 1. Recepten uit Apple Notities exporteren

1. Open **Script Editor** op je Mac (Spotlight → "Script Editor").
2. Open `export_notities.applescript` uit deze map.
3. Pas bovenaan `notesFolderName` aan naar de exacte naam van je map in
   Notities (bv. "Recepten").
4. Druk op ▶ (Run). Kies een lege map om naartoe te exporteren.
5. Je krijgt nu één `.txt` bestand per recept (titel = bestandsnaam, inhoud =
   platte tekst van de notitie).

## 2. App installeren

```bash
cd recipe-app
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Recepten importeren

```bash
python import_notes.py /pad/naar/geëxporteerde/map
```

Let op: de tekst uit Notities is vrije tekst, dus dit script **splitst niet
automatisch** in ingrediënten en bereidingsstappen — dat is te onbetrouwbaar om
blind te vertrouwen. Elk geïmporteerd recept krijgt:

- de notitie-titel als receptnaam
- de volledige tekst in het "Notities"-veld
- de tag `te-verwerken`

Open zo'n recept daarna in de app, klik **Bewerken**, en knip-en-plak de
ingrediënten/stappen vanuit het notities-veld naar de juiste velden (duurt
meestal minder dan een minuut per recept). Zodra je tevreden bent, haal je de
tag `te-verwerken` weg.

## 4. App starten

```bash
python app.py
```

Ga naar `http://localhost:5050` in je browser. Op je telefoon (zelfde wifi):
`http://<IP-van-je-Mac>:5050`.

## Ingrediënten invoeren

In het bewerk-scherm typ je één ingrediënt per regel:

```
300 g kipfilet
1 el olijfolie
2 tenen knoflook
2 eieren
```

De app herkent het getal en de eenheid vooraan; de rest is de naam. Op de
receptpagina kun je daarna live het aantal porties aanpassen — de
hoeveelheden worden automatisch herberekend.

## Data & back-up

Alles staat in `recepten.db` (SQLite) en `static/uploads/` (foto's). Zorg dat
je deze twee af en toe back-upt (bv. kopiëren naar iCloud Drive of een externe
schijf).
