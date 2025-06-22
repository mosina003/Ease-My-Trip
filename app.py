from flask import Flask, render_template, request, redirect, send_file, session, flash, jsonify
import sqlite3   
from datetime import datetime
import os
from fpdf import FPDF
from uuid import uuid4
import qrcode
import base64
import io

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
                status TEXT,
                user_source TEXT,
                user_destination TEXT
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
    local_trains_chennai = [
    ('Chennai Local 001', 'Chennai Beach', 'Tambaram', '05:00 AM', 10.0, 200),
    ('Chennai Local 002', 'Chennai Central', 'Velachery', '05:30 AM', 12.0, 200),
    ('Chennai Local 003', 'Chennai Beach', 'Chengalpattu', '06:00 AM', 15.0, 200),
    ('Chennai Local 004', 'Tambaram', 'Chennai Beach', '06:15 AM', 10.0, 200),
    ('Chennai Local 005', 'Velachery', 'Chennai Central', '06:30 AM', 12.0, 200),
    ('Chennai Local 006', 'Chengalpattu', 'Chennai Beach', '07:00 AM', 15.0, 200),
    ('Chennai Local 007', 'Chennai Central', 'Avadi', '07:10 AM', 8.0, 200),
    ('Chennai Local 008', 'Avadi', 'Chennai Central', '07:25 AM', 8.0, 200),
    ('Chennai Local 009', 'Chennai Beach', 'Tambaram', '07:45 AM', 10.0, 200),
    ('Chennai Local 010', 'Tambaram', 'Chennai Beach', '08:00 AM', 10.0, 200),
    ('Chennai Local 011', 'Velachery', 'Tambaram', '08:15 AM', 10.0, 200),
    ('Chennai Local 012', 'Tambaram', 'Velachery', '08:45 AM', 10.0, 200),
    ('Chennai Local 013', 'Chennai Central', 'Thiruninravur', '09:00 AM', 9.0, 200),
    ('Chennai Local 014', 'Thiruninravur', 'Chennai Central', '09:30 AM', 9.0, 200),
    ('Chennai Local 015', 'Chengalpattu', 'Tambaram', '10:00 AM', 10.0, 200),
    ('Chennai Local 016', 'Tambaram', 'Chengalpattu', '10:30 AM', 10.0, 200),
    ('Chennai Local 017', 'Chennai Beach', 'Velachery', '11:00 AM', 12.0, 200),
    ('Chennai Local 018', 'Velachery', 'Chennai Beach', '11:30 AM', 12.0, 200),
    ('Chennai Local 019', 'Chennai Central', 'Gummidipoondi', '12:00 PM', 18.0, 200),
    ('Chennai Local 020', 'Gummidipoondi', 'Chennai Central', '12:30 PM', 18.0, 200),
    ('Chennai Local 021', 'Chennai Central', 'Perambur', '01:00 PM', 5.0, 200),
    ('Chennai Local 022', 'Perambur', 'Chennai Central', '01:30 PM', 5.0, 200),
    ('Chennai Local 023', 'Chennai Beach', 'Tambaram', '02:00 PM', 10.0, 200),
    ('Chennai Local 024', 'Tambaram', 'Chennai Beach', '02:30 PM', 10.0, 200),
    ('Chennai Local 025', 'Velachery', 'Avadi', '03:00 PM', 13.0, 200),
    ('Chennai Local 026', 'Avadi', 'Velachery', '03:30 PM', 13.0, 200),
    ('Chennai Local 027', 'Chennai Central', 'Tiruvallur', '04:00 PM', 14.0, 200),
    ('Chennai Local 028', 'Tiruvallur', 'Chennai Central', '04:30 PM', 14.0, 200),
    ('Chennai Local 029', 'Chennai Beach', 'Chengalpattu', '05:00 PM', 15.0, 200),
    ('Chennai Local 030', 'Chengalpattu', 'Chennai Beach', '05:30 PM', 15.0, 200),
    ('Chennai Local 031', 'Tambaram', 'Velachery', '06:00 PM', 10.0, 200),
    ('Chennai Local 032', 'Velachery', 'Tambaram', '06:30 PM', 10.0, 200),
    ('Chennai Local 033', 'Chennai Central', 'Avadi', '07:00 PM', 8.0, 200),
    ('Chennai Local 034', 'Avadi', 'Chennai Central', '07:30 PM', 8.0, 200),
    ('Chennai Local 035', 'Chennai Beach', 'Tambaram', '08:00 PM', 10.0, 200),
    ('Chennai Local 036', 'Tambaram', 'Chennai Beach', '08:30 PM', 10.0, 200),
    ('Chennai Local 037', 'Velachery', 'Chennai Central', '09:00 PM', 12.0, 200),
    ('Chennai Local 038', 'Chennai Central', 'Velachery', '09:30 PM', 12.0, 200),
    ('Chennai Local 039', 'Chennai Central', 'Korattur', '10:00 PM', 6.0, 200),
    ('Chennai Local 040', 'Korattur', 'Chennai Central', '10:30 PM', 6.0, 200),
    ('Chennai Local 041', 'Chennai Beach', 'Tambaram', '11:00 PM', 10.0, 200),
    ('Chennai Local 042', 'Tambaram', 'Chennai Beach', '11:30 PM', 10.0, 200),
    ('Chennai Local 043', 'Velachery', 'Guindy', '12:00 AM', 7.0, 200),
    ('Chennai Local 044', 'Guindy', 'Velachery', '12:30 AM', 7.0, 200),
    ('Chennai Local 045', 'Avadi', 'Tiruninravur', '01:00 AM', 6.0, 200),
    ('Chennai Local 046', 'Tiruninravur', 'Avadi', '01:30 AM', 6.0, 200),
    ('Chennai Local 047', 'Chengalpattu', 'Tiruvallur', '02:00 AM', 20.0, 200),
    ('Chennai Local 048', 'Tiruvallur', 'Chengalpattu', '02:30 AM', 20.0, 200),
    ('Chennai Local 049', 'Chennai Central', 'Thirumullaivoyal', '03:00 AM', 10.0, 200),
    ('Chennai Local 050', 'Thirumullaivoyal', 'Chennai Central', '03:30 AM', 10.0, 200),
]


    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Trains")
        count = c.fetchone()[0]

        if count == 0:
            c.executemany("""
                INSERT INTO Trains (name, source, destination, time, fare, seats)
                VALUES (?, ?, ?, ?, ?, ?)
            """, local_trains_chennai)
            conn.commit()
            return "Dummy trains added!"
        else:
            return "Trains already exist!"

            
@app.route('/reset_trains')
def reset_trains():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM Trains")
        conn.commit()
    return redirect('/create_dummy_trains')

    
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
        user_source = request.form.get('source')
        user_destination = request.form.get('destination')

        if not train_id or not quantity or not user_source or not user_destination:
            flash('Please fill in all required fields.', 'error')
            return redirect('/book_train')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
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
            c.execute("""
                INSERT INTO Bookings (user_id, train_id, quantity, timestamp, status, user_source, user_destination)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, train_id, quantity, timestamp, "Booked", user_source, user_destination))

            booking_id = c.lastrowid
            conn.commit()

            flash('Booking successful!', 'success')
            return redirect(f'/ticket/{booking_id}')

    return render_template('book_trains.html', trains=trains)

@app.route('/ticket/<int:booking_id>')
def ticket(booking_id):
    if 'user_id' not in session:
        flash('Please login to view your ticket.', 'error')
        return redirect('/user_login')

    user_id = session['user_id']

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT Bookings.id, Trains.name, Bookings.user_source, Bookings.user_destination, Bookings.quantity, Bookings.timestamp
            FROM Bookings
            JOIN Trains ON Bookings.train_id = Trains.id
            WHERE Bookings.id = ? AND Bookings.user_id = ?
        """, (booking_id, user_id))
        booking = c.fetchone()

    if not booking:
        flash('Ticket not found or access denied.', 'error')
        return redirect('/')

    booking_id, train_name, source, destination, quantity, timestamp = booking

    qr_data = f"Booking ID: {booking_id}\nTrain: {train_name}\nFrom: {source}\nTo: {destination}\nQuantity: {quantity}\nDate: {timestamp}"
    qr_img = qrcode.make(qr_data)

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
    pdf.cell(0, 10, txt=" Suburban Train Ticket", ln=True, align='C')
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
    pdf.cell(0, 8, txt="Please show this ticket during your travel.", ln=True)

    # Ensure tickets folder exists
    tickets_dir = os.path.join(app.root_path, "static", "tickets")
    os.makedirs(tickets_dir, exist_ok=True)

    # Save PDF to disk with a unique name
    filename = f"{uuid4().hex}.pdf"
    filepath = os.path.join(tickets_dir, filename)
    pdf.output(filepath)

    # Public URL for the PDF
    public_url = f"{request.url_root}static/tickets/{filename}"
    print("PDF Filename:", filename)
    print("PDF URL:", public_url)

    # Return Dialogflow fulfillment JSON
    return jsonify({
    "fulfillmentMessages": [
        {
            "payload": {
                "richContent": [
                    [
                        {
                            "type": "button",
                            "icon": {
                                "type": "chevron_right",
                                "color": "#FF9800"
                            },
                            "text": "🎫 Download Ticket",
                            "link": public_url
                        }
                    ]
                ]
            }
        }
    ]
})




if __name__ == '__main__':
    init_db()
    app.run(debug=True)