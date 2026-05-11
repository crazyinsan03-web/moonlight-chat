from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, emit, join_room  # join_room yahan add kiya
import sqlite3
from datetime import datetime
from calls.events import register_call_events

app = Flask(__name__)

# =========================
# SECRET KEY
# =========================

app.secret_key = "moonlight_secret"

# =========================
# SOCKET IO
# =========================

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

# Yahan add kar 👇
register_call_events(socketio)
# =========================
# ONLINE USERS
# =========================

online_users = []

# =========================
# DATABASE
# =========================

def init_db():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    # USERS TABLE

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        phone TEXT,
        password TEXT,
        profile TEXT

    )

    """)

    # MESSAGES TABLE

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS messages(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        time TEXT,
        seen TEXT DEFAULT 'no',
        msg_type TEXT DEFAULT 'text'

    )

    """)

    # FRIENDS TABLE

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS friends(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1 TEXT,
        user2 TEXT

    )

    """)

    conn.commit()
    conn.close()

# START DATABASE

init_db()

# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        phone = request.form["phone"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")

        cursor = conn.cursor()

        cursor.execute("""

        SELECT * FROM users
        WHERE phone=? AND password=?

        """, (phone, password))

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user"] = user[1]

            return redirect("/home")

        else:

            return "Wrong Phone Number or Password"

    return render_template("login.html")

# =========================
# SIGNUP
# =========================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        fullname = request.form["fullname"]
        phone = request.form["phone"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")

        cursor = conn.cursor()

        # CHECK PHONE EXISTS

        cursor.execute("""

        SELECT * FROM users
        WHERE phone=?

        """, (phone,))

        already = cursor.fetchone()

        if already:

            conn.close()

            return "Phone Number Already Exists"

        # INSERT USER

        cursor.execute("""

        INSERT INTO users(
            fullname,
            phone,
            password
        )

        VALUES (?, ?, ?)

        """, (

            fullname,
            phone,
            password

        ))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("signup.html")

# =========================
# HOME
# =========================

@app.route("/home")
def home():

    if "user" not in session:

        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    # LOAD FRIENDS

    cursor.execute("""

    SELECT user2 FROM friends
    WHERE user1=?

    """, (username,))

    friends = cursor.fetchall()

    users = []

    # LAST MESSAGE

    for friend in friends:

        friend_name = friend[0]

        cursor.execute("""

        SELECT message, time
        FROM messages

        WHERE

        (sender=? AND receiver=?)

        OR

        (sender=? AND receiver=?)

        ORDER BY id DESC
        LIMIT 1

        """, (

            username,
            friend_name,

            friend_name,
            username

        ))

        last_msg = cursor.fetchone()

        if last_msg:

            message = last_msg[0]
            time = last_msg[1]

        else:

            message = "No messages yet"
            time = ""

        users.append({

            "name": friend_name,
            "message": message,
            "time": time

        })

    conn.close()

    return render_template(

        "home.html",

        username=username,
        users=users,
        online_users=online_users

    )

# =========================
# CHAT
# =========================

@app.route("/chat/<friend>", methods=["GET", "POST"])
def chat(friend):

    if "user" not in session:

        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    # =========================
    # SEEN UPDATE
    # =========================

    cursor.execute("""

    UPDATE messages

    SET seen='yes'

    WHERE receiver=?
    AND sender=?

    """, (

        username,
        friend

    ))

    conn.commit()

    # =========================
    # SEND MESSAGE
    # =========================

    if request.method == "POST":

        message = request.form["message"]

        if message.strip() == "":

            return "", 204

        current_time = datetime.now().strftime("%I:%M %p")

        cursor.execute("""

        INSERT INTO messages(

            sender,
            receiver,
            message,
            time,
            seen

        )

        VALUES (?, ?, ?, ?, ?)

        """, (

            username,
            friend,
            message,
            current_time,
            "no"

        ))

        conn.commit()

        return "", 204

    # =========================
    # LOAD CHATS
    # =========================

    cursor.execute("""

    SELECT * FROM messages

    WHERE

    (sender=? AND receiver=?)

    OR

    (sender=? AND receiver=?)

    ORDER BY id ASC

    """, (

        username,
        friend,

        friend,
        username

    ))

    messages = cursor.fetchall()

    conn.close()

    return render_template(

        "chat.html",

        username=username,
        friend=friend,
        messages=messages,
        online_users=online_users

    )

# =========================
# PROFILE
# =========================

@app.route("/profile")
def profile():

    if "user" not in session:

        return redirect("/")

    username = session["user"]

    return render_template(

        "profile.html",

        username=username

    )

# =========================
# ADD FRIEND
# =========================

@app.route("/addfriend", methods=["GET", "POST"])
def addfriend():

    if "user" not in session:

        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    users = []

    if request.method == "POST":

        search = request.form["search"]

        cursor.execute("""

        SELECT fullname FROM users

        WHERE fullname LIKE ?
        AND fullname != ?

        """, (

            '%' + search + '%',
            username

        ))

        users = cursor.fetchall()

    conn.close()

    return render_template(

        "addfriend.html",

        users=users

    )

# =========================
# ADD USER
# =========================

@app.route("/add/<friend>")
def add(friend):

    if "user" not in session:

        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    # CHECK EXISTS

    cursor.execute("""

    SELECT * FROM friends

    WHERE user1=? AND user2=?

    """, (

        username,
        friend

    ))

    already = cursor.fetchone()

    # ADD BOTH SIDES

    if not already:

        cursor.execute("""

        INSERT INTO friends(user1, user2)
        VALUES (?, ?)

        """, (

            username,
            friend

        ))

        cursor.execute("""

        INSERT INTO friends(user1, user2)
        VALUES (?, ?)

        """, (

            friend,
            username

        ))

        conn.commit()

    conn.close()

    return redirect("/home")

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/")

# =========================
# USER CONNECT
# =========================

@socketio.on("connect")
def connect_user():
    if "user" in session:
        username = session["user"]
        
        # YE LINE ADD KAR 👇
        join_room(username) 
        print(f"DEBUG: {username} joined their room") # Testing ke liye

        if username not in online_users:
            online_users.append(username)

        emit(
            "user_status",
            {
                "user": username,
                "status": "online"
            },
            broadcast=True
        )

# =========================
# USER DISCONNECT
# =========================

@socketio.on("disconnect")
def disconnect_user():

    if "user" in session:

        username = session["user"]

        if username in online_users:

            online_users.remove(username)

        emit(

            "user_status",

            {
                "user": username,
                "status": "offline"
            },

            broadcast=True

        )

# =========================
# TYPING
# =========================

@socketio.on("typing")
def typing(data):

    emit(

        "show_typing",

        data,

        broadcast=True

    )

# =========================
# SOCKET MESSAGE
# =========================

@socketio.on("send_message")
def handle_message(data):

    emit(

        "receive_message",

        data,

        broadcast=True

    )

# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    socketio.run(

        app,

        debug=True,

        host="0.0.0.0",

        port=5000

    )