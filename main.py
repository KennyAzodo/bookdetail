import json
import re
import os
import traceback

import requests
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Integer, select
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

API_KEY = os.environ.get('API_KEY')

# Create the Flask app
app = Flask(__name__)

# Configure the database URL (SQLite in this case)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI','sqlite:///book.db')
app.secret_key = 'Thesecret ishere'

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Define the User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # One-to-One relationship with Favourite
    favourite = db.relationship('Favourite', uselist=False, backref='user')


class Favourite(db.Model):
    __tablename__ = 'favourites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Remove unique=True
    book_title = db.Column(db.String(150), nullable=False)
    book_subtitle = db.Column(db.String(150))
    book_description = db.Column(db.String(15000), nullable=False)
    book_author = db.Column(db.String(150), nullable=False)


# Create the tables in the database
with app.app_context():
    print("Creating tables...")
    db.create_all()
    print("Tables created.")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_book = request.form.get('query')
        response = requests.get(
            f"https://www.googleapis.com/books/v1/volumes?q={user_book}&key={API_KEY}&fields=items(id,volumeInfo(title,authors))")
        response.raise_for_status()
        if not current_user.is_authenticated:
            flash('Login to be able to use this function')
            return redirect(url_for('home'))
        if response.status_code == 200:
            data = response.json()
            return render_template('search_results.html', books=data['items'])  # Pass books to template
        else:
            flash('Error retrieving data from Google Books API', 'error')
            return redirect(url_for('home'))  # Redirect to home or appropriate page
    return render_template('home.html', current_user=current_user)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Debugging statements

        # Validate required fields
        if not first_name or not last_name or not email or not password:
            flash('Please fill in all fields!', 'error')
            return redirect(url_for('signup'))

        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))

        # Check if email already exists
        stmt = select(User).where(User.email == email)
        existing_user = db.session.execute(stmt).scalar_one_or_none()

        if existing_user:
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))

        # Hash the password and create a new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(firstname=first_name,
                        lastname=last_name,
                        email=email,
                        password=hashed_password)

        # Add and commit the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            print("First Name:", first_name)
            print("Last Name:", last_name)
            print("Email:", email)
            print("Password (hashed):", hashed_password)
            db.session.rollback()  # Rollback the transaction on error
            flash('An error occurred during signup.', 'error')
            print("Error occurred during signup:")
            print(traceback.format_exc())  # Log full stack trace
            return redirect(url_for('signup'))
        return redirect(url_for('home'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        stmt = select(User).where(User.email == email)
        existing_user = db.session.execute(stmt).scalar_one_or_none()
        if not existing_user:
            flash('User is not registered, sign up instead', 'error')
            return redirect(url_for('signup'))

        user = existing_user  # Get the user object

        if not check_password_hash(user.password, request.form.get('password')):
            flash('Password is not correct! Try again', 'error')
            return redirect(url_for('login'))

        login_user(user)
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/search', methods=['GET', 'POST'])
@login_required  # Require the user to be logged in
def search():
    if request.method == 'POST':
        user_book = request.form.get('query')
        response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={user_book}&key={API_KEY}")
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            return render_template('search_results.html', books=data.get('items', []))  # Pass books to template
        else:
            flash('Error retrieving data from Google Books API', 'error')
            return redirect(url_for('home'))  # Redirect to home or appropriate page

    return render_template('search.html')  # Render search form for GET requests


@app.route('/receive/<post_id>', methods =['GET','POST'])
def receive(post_id):
    datas = requests.get(f'https://www.googleapis.com/books/v1/volumes/{post_id}')
    data = datas.json()
    print(data)
    book_details = {
        "title": data["volumeInfo"].get('title'),
        "subtitle": data["volumeInfo"].get("subtitle"),
        "authors": data["volumeInfo"].get("authors"),
        "description": data["volumeInfo"].get("description"),
    }
    if request.method == 'POST':
        # Assuming the user is logged in and current_user is set
        new_favourite = Favourite(
            user_id = current_user.id,
            book_title=book_details["title"],
            book_subtitle=book_details["subtitle"]  if book_details["subtitle"] else None,
            book_author=", ".join(book_details["authors"]) if book_details["authors"] else None,
            book_description=book_details["description"]
        )
        db.session.add(new_favourite)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('receive.html', **book_details, post_id=post_id)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))




@app.route('/favourite')
@login_required
def favourite():
    # Build the SQLAlchemy select statement to get the user's favourite books
    stmt = select(Favourite).where(Favourite.user_id == current_user.id)

    # Execute the statement
    result = db.session.execute(stmt)

    # Fetch all results as a list of Favourite objects
    user_favourites = result.scalars().all()

    # Pass the list of user's favourite books to the template
    return render_template('favourite.html', favourites=user_favourites)


if __name__ == "__main__":
    app.run(debug=True)
