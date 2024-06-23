from flask import Flask, render_template, request, redirect, url_for, flash # type: ignore
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash

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

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/home', methods = ['GET','POST'])
@login_required
def home():
    user_status = "Logged In"
    
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
    
		# #Update balance
        # if transaction['type'] == 'Income':
        #     balance += transaction['amount']
        # elif transaction['type'] == 'Expense':
        #     balance -= transaction['amount']
        
        # return redirect(url_for('home'))
        
    # Retrieve all transactions and the initial balance
    transactions = Transaction.query.all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0
    balance = initial_balance + sum(
        t.amount if t.type == 'Income' else -t.amount for t in transactions
    )        
    
    return render_template('home.html', transactions=transactions, balance=balance, initial_balance=initial_balance,
                           user=current_user,status=user_status)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=20)])
    confirm = PasswordField('Confirm Password', validators=[InputRequired(), Length(min=4, max=20)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=20)])
    submit = SubmitField('Login')
    
# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
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

#Below is the list to store data before database opiton used
# transactions = []
# initial_balance = 0.0
# balance = initial_balance



# def home():
#     global balance
#     if request.method == 'POST':
#         transaction = {
# 		'date': request.form.get('date'),
# 		'description': request.form.get('description'),
# 		'amount': float(request.form.get('amount')),
# 		'type': request.form.get('type'),
# 		}
#         transactions.append(transaction)

#@app.route('/set-initial-balance',methods=['POST'])
# def set_initial_balance():
#     global initial_balance,balance
#     initial_balance = float(request.form.get('initial_balance'))
#     balance = initial_balance
#     return redirect(url_for('home'))
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

#Create the database tables
with app.app_context():
    db.create_all()


if __name__ == "__main__":
	app.run(debug=True)
