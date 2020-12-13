import os

import bcrypt
from flask import Flask, redirect, render_template, request, session, url_for
from models import database, Likes, PartsOfSpeech, Translations, Users


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')


@app.before_request
def _db_connect():
    database.connect()


@app.teardown_request
def _db_close(_):
    if not database.is_closed():
        database.close()


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    name = request.form["name"]
    mail = request.form["mail"]
    password = request.form["password"].encode("utf-8")
    if password != request.form["password1"].encode("utf-8"):
        return render_template("register.html")
    password = hash_password(password)
    Users.insert(name=name, mail=mail, password=password, role_id=1).execute()
    return redirect(url_for("login"))


@app.route("/")
def start():
    return redirect(url_for("register"))


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password, salt)
    return hashed_password


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    mail = request.form["mail"]
    if mail is None:
        return render_template("login_failed.html", message='לא הוכנס דוא"ל!')
    user = Users.select().where(Users.mail == mail).get()
    if not user:
        return render_template("login_failed.html", message="המשתמש אינו קיים!")
    password = request.form["password"].encode("utf-8")
    if bcrypt.checkpw(password, str(user.password).encode("utf-8")):
        session["mail"] = user.mail
        session["name"] = user.name
        session["role"] = user.role_id
        return redirect(url_for("search"))
    return render_template("login_failed.html", message="שם משתמש או סיסמה אינם נכונים")


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    for item in ("mail", "name", "role"):
        session.pop(item, None)
    return redirect(url_for("register"))


@app.route("/search")
def search():
    word = request.args.get("word")
    if not word:
        return render_template("search.html",
                               mail=session["mail"],
                               name=session["name"],
                               role=session["role"])
    word = word.lower()
    translations = get_translation(word)
    if len(translations) == 0:
        translations = None
    else:
        translations = translations_to_display(translations)
    return render_template("search.html",
                           word=word,
                           translations=translations,
                           mail=session["mail"],
                           name=session["name"],
                           role=session["role"])


def translations_to_display(translations):
    new_t = []
    for i, t in enumerate(translations):
        word = t.word
        translation = t.translation
        part = t.part_of_speech.name
        explanation = t.explanation
        updated_by = t.updated_by
        if updated_by is not None:
            updated_by = updated_by.name
        likes = count_likes(word, translation)
        message = get_like_message(word, translation)
        new_t.append((translation, part, explanation, updated_by, i, message, likes))
    return new_t


def get_translation(word):
    word = word.lower()
    query = Translations.select().where((Translations.word == word) & (Translations.confirmed == 1))
    results = list(query)
    return results


@app.route("/upload", methods=["GET", "POST"])
def add_word():
    if request.method == "GET":
        return render_template("upload.html", parts=get_parts_dict().values())
    word = request.form["word"]
    if not word:
        return render_template("upload.html", parts=get_parts_dict().values())
    word = word.lower()
    translation = request.form["translation"]
    if not translation:
        return render_template("upload.html", parts=get_parts_dict().values())
    part_id = get_parts_dict(name_to_id=True)[request.form["parts_of_speech"]]
    explanation = request.form["explanation"]
    if not explanation:
        explanation = None
    Translations.insert(word=word,
                        translation=translation,
                        updated_by=session["mail"],
                        part_of_speech_id=part_id,
                        explanation=explanation,
                        confirmed=False).execute()
    return redirect(url_for("search"))


def get_parts_dict(name_to_id=False):
    query = PartsOfSpeech.select()
    if name_to_id:
        results = [(result.name, result.id) for result in query]
    else:
        results = [(result.id, result.name) for result in query]
    return dict(results)


@app.route("/check")
def check_words():
    words = [(t.word, t.translation, t.part_of_speech.name, t.explanation) for t in words_to_confirm()]
    return render_template("check.html", words=words)


@app.route("/confirm/<word>/<translation>", methods=["GET", "POST"])
def confirm_word(word, translation):
    Translations.update({Translations.confirmed: True}).where(
        (Translations.word == word) and (Translations.translation == translation)).execute()
    return redirect(url_for("check_words"))


@app.route("/delete/<word>/<translation>", methods=["GET", "POST"])
def delete_word(word, translation):
    value = Translations.select().where((Translations.word == word) and (Translations.translation == translation)).get()
    value.delete_instance()
    return redirect(url_for("check_words"))


def words_to_confirm():
    query = Translations.select().where(Translations.confirmed == 0)
    results = list(query)
    return results


def get_like_message(word, translation):
    value = list(Likes.select().where((Likes.word == word)
                                      & (Likes.translation == translation) & (Likes.user == session["mail"])))
    if len(value) == 0:
        return "like"
    return "dislike"


def count_likes(word, translation):
    return Likes.select().where((Likes.word == word)
                                and (Likes.translation == translation)).count()


@app.route("/like/<word>/<translation>", methods=["GET", "POST"])
def like_click(word, translation):
    value = list(Likes.select().where((Likes.word == word)
                                      & (Likes.translation == translation) & (Likes.user == session["mail"])))
    if len(value) == 0:
        Likes.insert(word=word,
                     translation=translation,
                     user=session["mail"]).execute()
    else:
        like = value[0]
        like.delete_instance()
    return redirect(f"/search?word={word}")
