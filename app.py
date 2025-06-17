from flask import Flask, render_template, request, redirect, send_file, session, flash, jsonify
import sqlite3   
from datetime import datetime
import os
from fpdf import FPDF
from uuid import uuid4

app = Flask(__name__)
app.secret_key="mosina"

def init_db():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT UNIQUE NOT NULL,
                password TEXT
            )
        ''')
        # Trains table
        c.execute('''
            CREATE TABLE IF NOT EXISTS Trains (
                id INTEGER PRIMARY KEY,
                name TEXT,
                source TEXT,
                destination TEXT,
                time TEXT,
                fare REAL,
                seats INTEGER
            )
        ''')
        # Bookings table
        c.execute('''
            CREATE TABLE IF NOT EXISTS Bookings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                train_id INTEGER,
                quantity INTEGER,
                timestamp TEXT,
                status TEXT
            )
        ''')
        conn.commit()


@app.route('/')
def welcome():
    return render_template("welcome.html")

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        print(f"Login attempt with Email: '{email}', Password: '{password}'")

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM Users WHERE lower(email) = lower(?)", (email,))
            user = c.fetchone()

            if user:
                print(f"User from DB: ID={user[0]}, Password='{user[1]}' (length {len(user[1])})")
            else:
                print("No user found with that email")

        if user and user[1].strip() == password:
            session['user_id'] = user[0]
            flash('Logged in successfully!', 'success')
            return redirect('/')
        else:
            flash('Invalid email or password', 'error')

    return render_template('user_login.html')



@app.route('/search_trains')
def search_trains():
    return "<h2>Search Trains Page (Coming Soon)</h2>"

@app.route('/all_trains')
def all_trains():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, source, destination, time, fare, seats FROM Trains")
        trains = c.fetchall()
    return render_template('all_trains.html', trains=trains)

@app.route('/search_train', methods=['GET', 'POST'])
def search_train():
    message = ''
    if request.method == 'POST':
        source = request.form.get('source', '').strip().lower()
        destination = request.form.get('destination', '').strip().lower()
        time_input = request.form.get('time', '').strip()

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, name, source, destination, time, fare, seats
                FROM Trains
                WHERE lower(source) = ? AND lower(destination) = ? AND time = ?
            """, (source, destination, time_input))
            matched = c.fetchall()

            if matched:
                message = "✅ Train is available at your preferred time!"
            else:
                c.execute("""
                    SELECT time
                    FROM Trains
                    WHERE lower(source) = ? AND lower(destination) = ?
                    ORDER BY time ASC
                """, (source, destination))
                next_train = c.fetchone()
                if next_train:
                    message = f"⚠️ Train is not available at {time_input}. Next available train is at {next_train[0]}."
                else:
                    message = "❌ No trains available for the selected route."

    return render_template('search_train.html', message=message)




@app.route('/user_registration', methods=['GET', 'POST'])
def user_registration():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()

            # Check if email already exists
            c.execute("SELECT id FROM Users WHERE email = ?", (email,))
            existing_user = c.fetchone()

            if existing_user:
                flash('Email already exists. Please use a different email.', 'error')
                return render_template('user_registration.html')

            # Insert new user
            c.execute("INSERT INTO Users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, password))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect('/user_login')

    return render_template('user_registration.html')


@app.route('/create_dummy_trains')
def create_dummy_trains():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        dummy_trains = [
            ('Express 101', 'New York', 'Chicago', '08:00 AM', 150.00, 100),
            ('Fastline 202', 'Los Angeles', 'San Francisco', '09:30 AM', 120.00, 80),
            ('Night Rider 303', 'Boston', 'Washington', '10:15 PM', 200.00, 60),
            ('Superfast 404', 'Miami', 'Orlando', '07:00 AM', 90.00, 50)
        ]
        c.executemany("INSERT INTO Trains (name, source, destination, time, fare, seats) VALUES (?, ?, ?, ?, ?, ?)", dummy_trains)
        conn.commit()
    return "Dummy trains added!"
    
from datetime import datetime

@app.route('/book_train', methods=['GET', 'POST'])
def book_train():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to book tickets.', 'error')
        return redirect('/user_login')

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, source, destination, time, fare, seats FROM Trains")
        trains = c.fetchall()

    if request.method == 'POST':
        train_id = request.form.get('train_id')
        quantity = request.form.get('quantity')

        if not train_id or not quantity:
            flash('Please select a train and quantity before booking.', 'error')
            return redirect('/book_train')

        try:
            quantity = int(quantity)
        except ValueError:
            flash('Invalid quantity.', 'error')
            return redirect('/book_train')

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute("SELECT seats FROM Trains WHERE id = ?", (train_id,))
            available_seats = c.fetchone()

            if available_seats is None:
                flash('Invalid train selection.', 'error')
                return redirect('/book_train')

            available_seats = available_seats[0]

            if quantity > available_seats:
                flash(f'Only {available_seats} seats available. Please select a lower quantity.', 'error')
                return redirect('/book_train')

            new_seats = available_seats - quantity
            c.execute("UPDATE Trains SET seats = ? WHERE id = ?", (new_seats, train_id))

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO Bookings (user_id, train_id, quantity, timestamp, status) VALUES (?, ?, ?, ?, ?)",
                (user_id, train_id, quantity, timestamp, "Booked")
            )
            booking_id = c.lastrowid
            conn.commit()

            flash('Booking successful!', 'success')
            return redirect(f'/ticket/{booking_id}')

    return render_template('book_trains.html', trains=trains)


import qrcode
import io
import base64

@app.route('/ticket/<int:booking_id>')
def ticket(booking_id):
    if 'user_id' not in session:
        flash('Please login to view your ticket.', 'error')
        return redirect('/user_login')

    user_id = session['user_id']

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT Bookings.id, Trains.name, Bookings.quantity, Bookings.timestamp
            FROM Bookings
            JOIN Trains ON Bookings.train_id = Trains.id
            WHERE Bookings.id = ? AND Bookings.user_id = ?
        """, (booking_id, user_id))
        booking = c.fetchone()

    if not booking:
        flash('Ticket not found or access denied.', 'error')
        return redirect('/')

    # Prepare data to encode in QR
    booking_id, train_name, quantity, timestamp = booking
    qr_data = f"Booking ID: {booking_id}\nTrain: {train_name}\nQuantity: {quantity}\nDate: {timestamp}"

    # Generate QR code image
    qr_img = qrcode.make(qr_data)

    # Convert PIL image to base64 string to embed in HTML
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('ticket.html', booking=booking, qr_code=qr_base64)
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect('/')

@app.route('/chat')
def chat():
    return render_template('chat.html')

from flask import Flask, request, send_file
from fpdf import FPDF
import io




# … your existing imports and app setup …

@app.route('/generate-ticket', methods=['POST'])
def generate_ticket():
    print("Webhook called")
    body = request.get_json(force=True)
    print("Received body:", body)
    body   = request.get_json(force=True)
    params = body["queryResult"]["parameters"]

    name             = params["name"]
    source           = params["cityfrom"]
    destination      = params["cityto"]
    tickets          = params["quantity"]
    travel_class     = params["trainclass"]
    trip_type        = params["triptype"]
    differently_abled= params["differentlyabled"]

    # Build PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt="🎫 Suburban Train Ticket", ln=True, align='C')
    pdf.ln(5)
    for label, val in [
        ("Name", name),
        ("From", source),
        ("To", destination),
        ("Tickets", tickets),
        ("Class", travel_class),
        ("Trip Type", trip_type),
        ("Differently Abled", differently_abled),
    ]:
        pdf.cell(0, 8, txt=f"{label}: {val}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, txt="✅ Please show this ticket during your travel.", ln=True)

    # Ensure tickets folder exists
    tickets_dir = os.path.join(app.root_path, "static", "tickets")
    os.makedirs(tickets_dir, exist_ok=True)

    # Save PDF to disk with a unique name
    filename = f"{uuid4().hex}.pdf"
    filepath = os.path.join(tickets_dir, filename)
    pdf.output(filepath)

    # Public URL for the PDF
    public_url = f"{request.url_root}static/tickets/{filename}"

    # Return Dialogflow fulfillment JSON
    return jsonify({
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [
                        f"Your ticket is ready! Download it here: {public_url}"
                    ]
                }
            }
        ]
    })





if __name__ == '__main__':
    init_db()
    app.run(debug=True)