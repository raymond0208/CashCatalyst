from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# Configuring the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cash_flow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view  = 'login'

#Define the authenticated user model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(80),nullable=False)

#User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Define the RegistrationForm class
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=20)])
    confirm = PasswordField('Confirm Password', validators=[InputRequired(), Length(min=4, max=20)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=20)])
    submit = SubmitField('Login')


# Define the Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(100),nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10),nullable=False)

# Define the InitialBalance model
class InitialBalance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, nullable=False)
    
    
# Helper function for balance calculation
def calculate_totals(transactions):
    cfo_types = ["Cash-customer", "Salary-suppliers", "Interest-paid", "Income-tax", "Other-cfo"]
    cfi_types = ["Buy-property-equipments", "Sell-property-equipments", "Buy-investment", "Sell-investment", "Other-cfi"]
    cff_types = ["Issue-shares", "borrowings", "Repay-borrowings", "Pay-dividends", "Other-cff"]

    total_cfo = sum(t.amount for t in transactions if t.type in cfo_types)
    total_cfi = sum(t.amount for t in transactions if t.type in cfi_types)
    total_cff = sum(t.amount for t in transactions if t.type in cff_types)
    
    return total_cfo, total_cfi, total_cff

# Routes

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/home', methods = ['GET','POST'])
@login_required
def home():
    user_status = "Logged In"
    
    page = request.args.get('page', 1, type=int)
    per_page = 8
    
    if request.method == 'POST':
        # Handle adding transactions
        transaction = Transaction(
            date=request.form.get('date'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount')),
            type=request.form.get('type')
        )
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('home'))
    
    transactions = Transaction.query.paginate(page=page, per_page=per_page)
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

    
    total_cfo, total_cfi, total_cff = calculate_totals(transactions)
    
    # Calculate balance
    balance = initial_balance + total_cfo + total_cfi + total_cff
    
    return render_template('home.html', transactions=transactions, balance=balance, initial_balance=initial_balance,
                           total_cfo=total_cfo, total_cfi=total_cfi, total_cff=total_cff, user=current_user,status=user_status)

@app.route('/edit/<int:transaction_id>', methods=['GET','POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if request.method == 'POST':
        transaction.date  = request.form['date']
        transaction.description = request.form['description']
        transaction.amount = float(request.form['amount'])
        transaction.type = request.form['type']
        db.session.commit()
        flash('Transaction Upldated Successfully', 'success')
        return redirect(url_for('home'))
    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    flash('Your Transaction Deleted!', 'danger')
    return redirect(url_for('home'))

    
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Debug print to check if form is validated
        print('Form Validated')
        
        user_exists = User.query.filter_by(username=form.username.data).first()
        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        print(f'User {form.username.data} registered successfully')
        
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    
    # Debug print to check if form validation failed    
    print('Form not validated')
    print(form.errors)
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))    

@app.route('/set-initial-balance', methods=['POST'])
def set_initial_balance():
    initial_balance_value = float(request.form.get('initial_balance'))
    initial_balance_record = InitialBalance.query.first()
    if initial_balance_record:
        initial_balance_record.balance = initial_balance_value
    else:
        initial_balance_record = InitialBalance(balance=initial_balance_value)
        db.session.add(initial_balance_record)
    
    #optional: clear transaction once initial value is set
    db.session.query(Transaction).delete()
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/export/<file_type>')
@login_required
def export(file_type):
    transactions = Transaction.query.all()
    data = [{
        'Date': transaction.date,
        'Description': transaction.description,
        'Amount': transaction.amount,
        'Type': transaction.type
    }for transaction in transactions]
    
    df = pd.DataFrame(data)
    
    if file_type == 'csv':
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='transactions.csv')
    elif file_type == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='transactions.xlsx')
    else:
        flash('Invalid file type requested.', 'danger')
        return redirect(url_for('home'))

@app.route('/balance-by-date', methods=['POST'])
@login_required
def balance_by_date():
    input_date = request.form.get('date')
    
    transactions = Transaction.query.filter(Transaction.date <= input_date).all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0
    
    total_cfo, total_cfi, total_cff = calculate_totals(transactions)

    balance_sum = initial_balance + total_cfo + total_cfi + total_cff
    
    #return render_template('home.html',balance_sum=balance_sum,date=input_date,total_cfo=total_cfo,total_cfi = total_cfi, total_cff=total_cff, user=current_user)
    return jsonify({
        'input_date': input_date,
        'balance_sum': balance_sum
    })

#Create the database tables
with app.app_context():
    db.create_all()


if __name__ == "__main__":
	app.run(debug=True)
