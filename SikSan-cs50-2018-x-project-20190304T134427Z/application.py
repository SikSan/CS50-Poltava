import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import logging
import datetime
import json


from helpers import apology, login_required, getSessionId

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///fbbf.db")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # log out
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # username check
        if not request.form.get("username"):
            return apology("Missing username!")

        # password and confirmation check
        elif not request.form.get("password") or request.form.get("confirmation") != request.form.get("password"):
            return apology("Incorrect password!")

        # avatar check
        elif not request.form.get("avatar"):
            return apology("Missing avatar!")

        # insert new row in db
        rows = db.execute("INSERT INTO users (username, hash, avatar) VALUES(:username, :hash, :avatar)", username=request.form.get("username"),
                          hash=generate_password_hash(request.form.get("password")), avatar=request.form.get("avatar"))

        # check for unique username
        if not rows:
            return apology("try again")

        # log in
        session["user_id"] = rows

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/")
@login_required
def index():
    """Main page"""
    # удаляем все законченные игры этого юзера
    db.execute("DELETE FROM gamesessions WHERE status = :s AND user1_id = :u", s="ended", u=session["user_id"])

    # время на данный момент
    current_time = datetime.datetime.now()

    # удаляем данные об играх, начатых больше часа назад
    db.execute("DELETE FROM gamesessions WHERE user2timestamp <= :u", u=current_time - datetime.timedelta(hours=1))
    db.execute("DELETE FROM games WHERE start_time <= :u", u=current_time - datetime.timedelta(hours=1))

    # выбираем все актуальные заявки для отображения в таблице
    challenges = db.execute("SELECT * FROM gamesessions WHERE status = :s", s="ready")

    # передаем список актуальных заявок для отображения и как джейсон в функцию джаваскрипта, чтоб сравнивать с новопоступившими и обновлять
    return render_template("index.html", challenges=challenges, challengesJSON=json.dumps(challenges))


@app.route("/index_refresh/", methods=["GET", "POST"])
@login_required
def index_refresh():
    """Refresh index page"""
    # время на данный момент
    current_time = datetime.datetime.now()

    # удаляем все заявки, которые не обновляются 10 сек
    db.execute("DELETE FROM gamesessions WHERE status = :s AND user1timestamp <= :u",
               u=current_time - datetime.timedelta(seconds=10), s="ready")

    # получаем список заявок, отображенных на странице
    challenges = json.loads(request.data)

    # получаем актуальные заявки
    challenges_new = db.execute("SELECT * FROM gamesessions WHERE status = :s", s="ready")
    # logging.warning(challenges)
    # logging.warning(challenges_new)

    # если список заявок со страницы пуст, назначаем пустой лист, если нет, вытягиваем из каждой ид сессии и помещаем в лист
    challenges_sessions = list(map(getSessionId, challenges)) if len(challenges) > 0 else []
    logging.warning(challenges_sessions)
    # то же самое с новыми заявками
    challenges_new_sessions = list(map(getSessionId, challenges_new)) if len(challenges_new) > 0 else []
    logging.warning(challenges_new_sessions)

    # сравниваем полученные листы, передаем результат в js
    if challenges_sessions == challenges_new_sessions:
        return jsonify(False)
    else:
        return jsonify(True)


@app.route("/fight/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a challenge"""
    # находим имя юзера
    name = db.execute("SELECT username FROM users WHERE id = :id", id=session["user_id"])

    # создаем новую геймсессию
    new_session = db.execute("INSERT INTO gamesessions (user1_id, username1) VALUES (:user1_id, :username1)",
                             user1_id=session["user_id"], username1=name[0]["username"])

    # проверка, есть ли у юзера созданные заявки (эта колонка юник в базе)
    if not new_session:
        return apology("You've already created a challenge")

    else:
        # достаем ид созданной сессии
        gamesession = db.execute("SELECT * FROM gamesessions WHERE user1_id = :user1_id", user1_id=session["user_id"])
        session_id = gamesession[0]["session_id"]
        # переход на путь стартгейм с передачей ид сессии
        return redirect("/startgame/" + str(session_id))


@app.route("/startgame/<int:session_id>")
@login_required
def startgame(session_id):
    """Starting the game"""

    # проверка на существование геймсессии
    session_check = db.execute("SELECT * FROM gamesessions WHERE session_id = :session_id", session_id=session_id)
    if len(session_check) == 1:
        # проверка, что игра еще в ожидании второго игрока
        if session_check[0]["status"] == "ready":
            # если это подключившийся
            if session_check[0]["user1_id"] != session["user_id"]:
                # вносим данные в бд
                db.execute("UPDATE gamesessions SET user2_id = :u2, status = :s, user2timestamp = CURRENT_TIMESTAMP WHERE session_id = :session_id",
                           u2=session["user_id"], s="playing", session_id=session_id)
                # достаем аватары и имена игроков
                user1 = db.execute("SELECT avatar FROM users WHERE id = :id", id=session_check[0]["user1_id"])
                user2 = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
                # помещаем данные в тейбл геймс, где будет информация о бое
                db.execute("INSERT INTO games (name1, name2, session_id, avatar1, avatar2, round) VALUES (:name1, :name2, :session_id, :avatar1, :avatar2, :r)",
                           name1=session_check[0]["username1"], name2=user2[0]["username"], session_id=session_id, avatar1=user1[0]["avatar"], avatar2=user2[0]["avatar"], r="0")
                # для начала игры ставим в геймсессии раунд 0
                db.execute("UPDATE gamesessions SET round = :r", r="0")
                return redirect("/fight/" + str(session_id))
            # если это создатель заявки
            else:

                # рендерим страничку ожидания
                return render_template("waitingplayer.html", session_id=session_id)

        else:
            # если это плеер один обновляет страничку после присоединения второго игрока
            if session_check[0]["user1_id"] == session["user_id"]:
                return redirect("/fight/" + str(session_id))
            # чек, если кто-то подключается, а игра уже играется или сыграна
            else:
                return apology("Sorry, the game is in progress")
    else:
        # чек, если кто-то подключается, а игры уже нет
        return apology("Sorry, the game doesn't exist")


@app.route("/checkplayer/<int:session_id>", methods=["GET", "POST"])
@login_required
def checkplayer(session_id):
    """Check player2 presence"""
    # достаем из бд геймсессию по ее ид
    session_check = db.execute("SELECT * FROM gamesessions WHERE session_id = :session_id", session_id=session_id)
    # проверяем статус, когда он обновится при подключении второго игрока и возвращаем bool exp в js
    if session_check[0]["status"] == "playing":
        return jsonify(True)
    else:
        # при каждом запросе до появления игрока2 ставим таймстамп для проверки актуальности заявки
        db.execute("UPDATE gamesessions SET user1timestamp = CURRENT_TIMESTAMP WHERE session_id = :session_id", session_id=session_id)
        return jsonify(False)


@app.route("/fight/<int:session_id>", methods=["GET", "POST"])
@login_required
def fight(session_id):
    """game page"""
    # чек существования игры
    session_check = db.execute("SELECT * FROM gamesessions WHERE session_id = :session_id", session_id=session_id)
    if len(session_check) == 1:

        # достаем имя игрока
        player = db.execute("SELECT username FROM users WHERE id = :id", id=session["user_id"])
        # если игра играется
        if session_check[0]["status"] == "playing":
            # достаем завершенный раунд
            r = session_check[0]["round"]
            # по раунду и ид сессии находим актуальную инфу о бое
            game = db.execute("SELECT * FROM games WHERE session_id = :session_id AND round = :r", session_id=session_id, r=r)
            name1 = game[0]["name1"]
            name2 = game[0]["name2"]
            health1 = game[0]["health1"]
            health2 = game[0]["health2"]
            avatar1 = game[0]["avatar1"]
            avatar2 = game[0]["avatar2"]

            if request.method == "POST":

                attack = request.form.get("attack")
                defence = request.form.get("defence")

                # если это игрок1
                if player[0]["username"] == name1:
                    # проверяем, походил ли противник (есть ли строка с информацией о текущем раунде)
                    turn = db.execute("SELECT * FROM games WHERE session_id = :session_id AND round = :r",
                                      session_id=session_id, r=r + 1)
                    # если походил
                    if len(turn) == 1:
                        # считаем урон
                        if turn[0]["attack2"] == defence:
                            damage2 = 0
                        else:
                            damage2 = 5
                            health1 = game[0]["health1"] - damage2

                        if turn[0]["defence2"] == attack:
                            damage1 = 0
                        else:
                            damage1 = 5
                            health2 = game[0]["health2"] - damage1

                        # обновляем строку с текущим раундом
                        db.execute("UPDATE games SET attack1 = :attack1, defence1 = :defence1, health1 = :health1, health2 = :health2, start_time = CURRENT_TIMESTAMP WHERE session_id = :session_id AND round = :r",
                                   session_id=session_id, r=r + 1, attack1=attack, defence1=defence, health1=health1, health2=health2)
                        # отмечаем в геймсессии этот раунд как завершенный
                        db.execute("UPDATE gamesessions SET round = :r", r=r + 1)
                        # если чье-то здоровье закончилось, меняем статус игры на завершенный и выдаем результат
                        if health1 == 0 and health2 == 0:
                            db.execute("UPDATE gamesessions SET status = :s", s="ended")
                            return render_template("draw.html")
                        if health1 == 0:
                            db.execute("UPDATE gamesessions SET status = :s", s="ended")
                            return render_template("defeat.html")
                        if health2 == 0:
                            db.execute("UPDATE gamesessions SET status = :s", s="ended")
                            return render_template("victory.html")

                        # если здоровье есть у обоих, рендерим темплейт для следующего хода
                        return render_template("fight.html", name1=name1, name2=name2, health1=health1, health2=health2, avatar1=avatar1, avatar2=avatar2, session_id=session_id)

                    # если игрок1 походил первым
                    else:
                        # инсертим строку нового раунда
                        db.execute("INSERT INTO games (name1, name2, session_id, avatar1, avatar2, round, attack1, defence1) VALUES (:name1, :name2, :session_id, :avatar1, :avatar2, :r, :attack1, :defence1)",
                                   name1=name1, name2=name2, session_id=session_id, avatar1=avatar1, avatar2=avatar2, r=r + 1, attack1=attack, defence1=defence)
                        # рендер темплейта ожидания
                        return render_template("waiting.html", name1=name1, name2=name2, health1=health1, health2=health2, avatar1=avatar1, avatar2=avatar2, session_id=session_id)

                # если это игрок2
                else:
                    # проверяем, походил ли противник (есть ли строка с информацией о текущем раунде)
                    turn = db.execute("SELECT * FROM games WHERE session_id = :session_id AND round = :r",
                                      session_id=session_id, r=r + 1)
                    # если походил
                    if len(turn) == 1:
                        # считаем урон
                        if turn[0]["attack1"] == defence:
                            damage1 = 0
                        else:
                            damage1 = 5
                        health2 = game[0]["health2"] - damage1

                        if turn[0]["defence1"] == attack:
                            damage2 = 0
                        else:
                            damage2 = 5
                        health1 = game[0]["health1"] - damage2

                        # обновляем строку с текущим раундом
                        db.execute("UPDATE games SET attack2 = :attack2, defence2 = :defence2, health2 = :health2, health1 = :health1, start_time = CURRENT_TIMESTAMP WHERE session_id = :session_id AND round = :r",
                                   session_id=session_id, r=r + 1, attack2=attack, defence2=defence, health1=health1, health2=health2)
                        # отмечаем в геймсессии этот раунд как завершенный
                        db.execute("UPDATE gamesessions SET round = :r", r=r + 1)
                        # если чье-то здоровье закончилось, меняем статус игры на завершенный и выдаем результат
                        if health1 == 0 and health2 == 0:
                            db.execute("UPDATE gamesessions SET status = :s", s="ended")
                            return render_template("draw.html")
                        if health2 == 0:
                            db.execute("UPDATE gamesessions SET status = :s", s="ended")
                            return render_template("defeat.html")
                        if health1 == 0:
                            db.execute("UPDATE gamesessions SET status = :s", s="ended")
                            return render_template("victory.html")

                        # если здоровье есть у обоих, рендерим темплейт для следующего хода
                        return render_template("fight.html", name1=name1, name2=name2, health1=health1, health2=health2, avatar1=avatar1, avatar2=avatar2, session_id=session_id)
                    # если игрок2 походил первым
                    else:
                        # инсертим строку нового раунда
                        db.execute("INSERT INTO games (name1, name2, session_id, avatar1, avatar2, round, attack2, defence2) VALUES (:name1, :name2, :session_id, :avatar1, :avatar2, :r, :attack2, :defence2)",
                                   name1=name1, name2=name2, session_id=session_id, avatar1=avatar1, avatar2=avatar2, r=r + 1, attack2=attack, defence2=defence)
                        # рендер темплейта ожидания
                        return render_template("waiting.html", name1=name1, name2=name2, health1=health1, health2=health2, avatar1=avatar1, avatar2=avatar2, session_id=session_id)

            else:  # GET
                if player[0]["username"] == name1 or player[0]["username"] == name2:
                    return render_template("fight.html", name1=name1, name2=name2, health1=health1, health2=health2, avatar1=avatar1, avatar2=avatar2, session_id=session_id)

        # если статус игры "закончена"
        elif session_check[0]["status"] == "ended":
            # достаем последний раунд
            r = session_check[0]["round"]
            # достаем информацию об этом раунде
            game = db.execute("SELECT * FROM games WHERE session_id = :session_id AND round = :r", session_id=session_id, r=r)
            name1 = game[0]["name1"]
            name2 = game[0]["name2"]
            health1 = game[0]["health1"]
            health2 = game[0]["health2"]
            # показываем результат, если это игрок1
            if player[0]["username"] == name1:
                if health1 == 0 and health2 == 0:
                    return render_template("draw.html")
                if health2 == 0:
                    return render_template("victory.html")
                if health1 == 0:
                    return render_template("defeat.html")
            # показываем результат, если это игрок2
            elif player[0]["username"] == name2:
                if health1 == 0 and health2 == 0:
                    return render_template("draw.html")
                if health2 == 0:
                    return render_template("defeat.html")
                if health1 == 0:
                    return render_template("victory.html")
            # чек, если это посторонний
            else:
                return apology("The game is over")

        # игры еще нет
        else:
            return apology("There is no game")
    # игра закончилась
    else:
        return apology("The game is over")


@app.route("/round_end/<int:session_id>", methods=["GET", "POST"])
@login_required
def round_end(session_id):
    """Check opponent's turn"""
    # достаем номер завершенного раунда
    session_check = db.execute("SELECT round FROM gamesessions WHERE session_id = :session_id", session_id=session_id)
    # проверяем, есть ли в игровом тейбле строка с новым раундом
    turn = db.execute("SELECT * FROM games WHERE session_id = :session_id AND round = :r",
                      session_id=session_id, r=session_check[0]["round"] + 1)
    if len(turn) == 1:
        return jsonify(False)
    else:
        return jsonify(True)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)