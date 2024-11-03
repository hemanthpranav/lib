# app.py
from flask import Flask, render_template, redirect, url_for, flash, request # type: ignore
from models import db, User, Book, Borrow
from forms import RegisterForm, LoginForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from datetime import datetime
import os
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create the database tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

# Admin Dashboard
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    books = Book.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', books=books, users=users)

# User Dashboard
@app.route('/user')
@login_required
def user_dashboard():
    borrows = Borrow.query.filter_by(user_id=current_user.id, return_date=None).all()
    return render_template('user_dashboard.html', borrows=borrows)

# Browse Books
@app.route('/browse')
@login_required
def browse_books():
    books = Book.query.all()
    return render_template('browse_books.html', books=books)

# Borrow Book
@app.route('/borrow/<int:book_id>', methods=['GET', 'POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    if not book.available:
        flash('Book is currently not available.', 'warning')
        return redirect(url_for('browse_books'))
    if request.method == 'POST':
        book.available = False
        borrow = Borrow(user_id=current_user.id, book_id=book.id)
        db.session.add(borrow)
        db.session.commit()
        flash(f'You have borrowed "{book.title}".', 'success')
        return redirect(url_for('user_dashboard'))
    return render_template('borrow_book.html', book=book)

# Return Book
@app.route('/return/<int:borrow_id>', methods=['GET', 'POST'])
@login_required
def return_book(borrow_id):
    borrow = Borrow.query.get_or_404(borrow_id)
    if borrow.user_id != current_user.id and current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        borrow.return_date = datetime.utcnow()
        borrow.book.available = True
        db.session.commit()
        flash(f'You have returned "{borrow.book.title}".', 'success')
        return redirect(url_for('user_dashboard'))
    return render_template('return_book.html', borrow=borrow)

# Add Book (Admin)
@app.route('/admin/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        new_book = Book(title=title, author=author)
        db.session.add(new_book)
        db.session.commit()
        flash(f'Book "{title}" added successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_book.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)