import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from typing_extensions import Annotated
from models import db, User, Transaction, InitialBalance
from forms import LoginForm, RegistrationForm
from anthropic_service import generate_financial_analysis
from upload_handler import process_upload
from utils import calculate_totals
from config import Config
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv

#load Anthropic LLM API key and other variables in .env
load_dotenv

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    #return User.query.get(int(user_id))
    return db.session.get(User, int(user_id))

#All routes in app
@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    user_status = "Logged In"
    page = request.args.get('page', 1, type=int)
    per_page = 8

    if request.method == 'POST':
        # Handle adding transactions
        new_transaction = Transaction(
            date=request.form.get('date'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount')),
            type=request.form.get('type')
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully', 'success')
        return redirect(url_for('home'))

    paginated_transactions = Transaction.query.order_by(Transaction.date.desc()).paginate(page=page, per_page=per_page)
    all_transactions = Transaction.query.all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

    total_cfo, total_cfi, total_cff = calculate_totals(all_transactions)
    balance = initial_balance + total_cfo + total_cfi + total_cff

    return render_template('home.html', transactions=paginated_transactions, balance=balance, initial_balance=initial_balance,
                           total_cfo=total_cfo, total_cfi=total_cfi, total_cff=total_cff, user=current_user, status=user_status)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register',methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user_exists = User.query.filter_by(username=form.username.data).first()
        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if request.method == 'POST':
        transaction.date = request.form['date']
        transaction.description = request.form['description']
        transaction.amount = float(request.form['amount'])
        transaction.type = request.form['type']
        db.session.commit()
        flash('Transaction Updated Successfully', 'success')
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

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_route():
    if request.method == 'GET':
        return render_template('upload.html')
    elif request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        try:
            result = process_upload(file)
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in upload_file: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/set-initial-balance', methods=['POST'])
@login_required
def set_initial_balance():
    initial_balance_value = float(request.form.get('initial_balance'))
    initial_balance_record = InitialBalance.query.first()
    if initial_balance_record:
        initial_balance_record.balance = initial_balance_value
    else:
        initial_balance_record = InitialBalance(balance=initial_balance_value)
        db.session.add(initial_balance_record)
    db.session.query(Transaction).delete()
    db.session.commit()
    flash('Initial balance set successfully', 'success')
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
    } for transaction in transactions]

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
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                         as_attachment=True, download_name='transactions.xlsx')
    else:
        flash('Invalid file type requested.', 'danger')
        return redirect(url_for('home'))

@app.route('/save_transactions', methods=['POST'])
@login_required
def save_transactions():
    data = request.json
    try:
        for item in data:
            new_transaction = Transaction(
                date=item['date'],
                description=item['description'],
                amount=float(item['amount']),
                type=item['type']
            )
            db.session.add(new_transaction)
        db.session.commit()
        return jsonify({'message': 'Transactions saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@app.route('/balance-by-date', methods=['POST'])
@login_required
def balance_by_date():
    input_date = request.form.get('date')
    transactions = Transaction.query.filter(Transaction.date <= input_date).all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0
    total_cfo, total_cfi, total_cff = calculate_totals(transactions)
    balance_sum = initial_balance + total_cfo + total_cfi + total_cff
    return jsonify({
        'input_date': input_date,
        'balance_sum': balance_sum
    })
    
@app.route('/forecast', methods=['GET'])
@login_required
def forecast():
    transactions = Transaction.query.order_by(Transaction.date).all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

    total_cfo, total_cfi, total_cff = calculate_totals(transactions)
    current_balance = initial_balance + total_cfo + total_cfi + total_cff

    transaction_data = "\n".join([f"Date: {t.date}, Amount: {t.amount}, Type: {t.type}" for t in transactions])

    try:
        analysis = generate_financial_analysis(
            initial_balance, current_balance, total_cfo, total_cfi, total_cff, transaction_data
        )
        return jsonify({'analysis': analysis})
    except ValueError as ve:
        app.logger.error(f"Configuration error: {str(ve)}")
        return jsonify({'error': 'API key not configured'}), 500
    except Exception as e:
        app.logger.error(f"Failed to generate analysis: {str(e)}")
        return jsonify({'error': 'Failed to generate analysis'}), 500

if __name__ == '__main__':
    app.run(debug=True)