import os
import cloudinary
import cloudinary.uploader

from flask import Flask, render_template, request, redirect, url_for, flash

from database import get_db, init_db

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "verander-dit")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

init_db()


@app.template_filter("fmt_amount")
def fmt_amount(value):
    if value is None:
        return ""
    value = float(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


# ---------- helpers ----------

KNOWN_UNITS = {
    "g", "kg", "ml", "l", "cl", "dl", "tl", "el", "stuks", "stuk",
    "snuf", "snufje", "teen", "tenen", "blikje", "blik", "plak", "plakken",
    "takje", "takjes", "bol", "bollen",
}


def parse_amount(raw):
    if not raw:
        return None
    raw = raw.replace(",", ".")
    if "/" in raw:
        try:
            num, denom = raw.split("/")
            return float(num) / float(denom)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_ingredient_line(line):
    """'300 g kipfilet' -> (300.0, 'g', 'kipfilet'); '2 eieren' -> (2.0, '', 'eieren')."""
    line = line.strip()
    if not line:
        return None
    tokens = line.split()
    amount = parse_amount(tokens[0])
    if amount is None:
        return (None, "", line)
    rest = tokens[1:]
    unit = ""
    if rest and rest[0].lower().strip(".,") in KNOWN_UNITS:
        unit = rest[0]
        rest = rest[1:]
    name = " ".join(rest).strip()
    if not name:
        name = unit
        unit = ""
    return (amount, unit, name)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_photo(file_storage):
    """Upload naar Cloudinary; geeft de publieke URL terug."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        flash("Ongeldig fotoformaat. Gebruik png, jpg, webp of gif.")
        return None
    result = cloudinary.uploader.upload(file_storage, folder="receptenkast")
    return result["secure_url"]


def load_recipe(recipe_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
        recipe = cur.fetchone()
        if recipe is None:
            db.close()
            return None, None, None
        cur.execute(
            "SELECT * FROM ingredients WHERE recipe_id = %s ORDER BY position", (recipe_id,)
        )
        ingredients = cur.fetchall()
        cur.execute(
            "SELECT * FROM steps WHERE recipe_id = %s ORDER BY position", (recipe_id,)
        )
        steps = cur.fetchall()
    db.close()
    return recipe, ingredients, steps


def all_tags():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT tags FROM recipes")
        rows = cur.fetchall()
    db.close()
    tag_set = set()
    for row in rows:
        for t in (row["tags"] or "").split(","):
            t = t.strip()
            if t:
                tag_set.add(t)
    return sorted(tag_set)


# ---------- routes ----------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    tag = request.args.get("tag", "").strip()
    db = get_db()

    query = """
        SELECT DISTINCT r.* FROM recipes r
        LEFT JOIN ingredients i ON i.recipe_id = r.id
        WHERE 1=1
    """
    params = []
    if q:
        query += " AND (r.title ILIKE %s OR i.name ILIKE %s)"
        like = f"%{q}%"
        params += [like, like]
    if tag:
        query += " AND (',' || r.tags || ',') LIKE %s"
        params.append(f"%,{tag},%")
    query += " ORDER BY r.created_at DESC"

    with db.cursor() as cur:
        cur.execute(query, params)
        recipes = cur.fetchall()
    db.close()
    return render_template(
        "index.html", recipes=recipes, q=q, active_tag=tag, tags=all_tags()
    )


@app.route("/recept/<int:recipe_id>")
def view_recipe(recipe_id):
    recipe, ingredients, steps = load_recipe(recipe_id)
    if recipe is None:
        flash("Recept niet gevonden.")
        return redirect(url_for("index"))
    return render_template("recipe.html", recipe=recipe, ingredients=ingredients, steps=steps)


@app.route("/recept/nieuw", methods=["GET", "POST"])
def new_recipe():
    if request.method == "GET":
        return render_template("edit.html", recipe=None, ingredients=[], steps=[])
    return save_recipe(None)


@app.route("/recept/<int:recipe_id>/bewerken", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "GET":
        recipe, ingredients, steps = load_recipe(recipe_id)
        if recipe is None:
            flash("Recept niet gevonden.")
            return redirect(url_for("index"))
        ingredients_text = "\n".join(
            f"{(str(i['amount']).rstrip('0').rstrip('.') if i['amount'] is not None else '')} "
            f"{i['unit']} {i['name']}".strip().replace("  ", " ")
            for i in ingredients
        )
        steps_text = "\n".join(s["instruction"] for s in steps)
        return render_template(
            "edit.html", recipe=recipe, ingredients_text=ingredients_text, steps_text=steps_text
        )
    return save_recipe(recipe_id)


def save_recipe(recipe_id):
    title = request.form.get("title", "").strip()
    servings = request.form.get("servings", "4").strip()
    tags_raw = request.form.get("tags", "").strip()
    tags = ",".join(t.strip() for t in tags_raw.split(",") if t.strip())
    notes = request.form.get("notes", "").strip()
    ingredients_raw = request.form.get("ingredients", "")
    steps_raw = request.form.get("steps", "")

    if not title:
        flash("Een titel is verplicht.")
        return redirect(request.referrer or url_for("index"))

    try:
        servings_int = max(1, int(servings))
    except ValueError:
        servings_int = 4

    db = get_db()
    photo_url = None
    if recipe_id is not None:
        with db.cursor() as cur:
            cur.execute("SELECT photo FROM recipes WHERE id = %s", (recipe_id,))
            existing = cur.fetchone()
        photo_url = existing["photo"] if existing else None

    uploaded = save_photo(request.files.get("photo"))
    if uploaded:
        photo_url = uploaded
    if request.form.get("remove_photo") == "1":
        photo_url = None

    with db:
        with db.cursor() as cur:
            if recipe_id is None:
                cur.execute(
                    "INSERT INTO recipes (title, servings, tags, notes, photo) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (title, servings_int, tags, notes, photo_url),
                )
                recipe_id = cur.fetchone()["id"]
            else:
                cur.execute(
                    "UPDATE recipes SET title=%s, servings=%s, tags=%s, notes=%s, photo=%s WHERE id=%s",
                    (title, servings_int, tags, notes, photo_url, recipe_id),
                )
                cur.execute("DELETE FROM ingredients WHERE recipe_id = %s", (recipe_id,))
                cur.execute("DELETE FROM steps WHERE recipe_id = %s", (recipe_id,))

            for pos, line in enumerate(l for l in ingredients_raw.splitlines() if l.strip()):
                parsed = parse_ingredient_line(line)
                if parsed:
                    amount, unit, name = parsed
                    if name:
                        cur.execute(
                            "INSERT INTO ingredients (recipe_id, position, amount, unit, name) VALUES (%s, %s, %s, %s, %s)",
                            (recipe_id, pos, amount, unit, name),
                        )

            for pos, line in enumerate(l for l in steps_raw.splitlines() if l.strip()):
                cur.execute(
                    "INSERT INTO steps (recipe_id, position, instruction) VALUES (%s, %s, %s)",
                    (recipe_id, pos, line.strip()),
                )

    db.close()
    return redirect(url_for("view_recipe", recipe_id=recipe_id))


@app.route("/recept/<int:recipe_id>/verwijderen", methods=["POST"])
def delete_recipe(recipe_id):
    db = get_db()
    with db:
        with db.cursor() as cur:
            cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    db.close()
    flash("Recept verwijderd.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
