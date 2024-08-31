import pandas as pd
from flask import current_app,jsonify,request
import os
from werkzeug.utils import secure_filename

#The dictionary of selection options and keywords
ALLOWED_TYPES = {
    "Cash-customer": ["cash", "customer", "receipt"],
    "Salary-suppliers": ["salary", "supplier", "employee", "payment"],
    "Interest-paid": ["interest", "paid"],
    "Income-tax": ["income", "tax"],
    "Other-cfo": ["operating", "cfo"],
    "Buy-property-equipments": ["buy", "purchase", "property", "equipment"],
    "Sell-property-equipments": ["sell", "sale", "property", "equipment"],
    "Buy-investment": ["buy", "purchase", "investment"],
    "Sell-investment": ["sell", "sale", "investment"],
    "Other-cfi": ["investing", "cfi"],
    "Issue-shares": ["issue", "share"],
    "borrowings": ["borrow", "loan"],
    "Repay-borrowings": ["repay", "repayment"],
    "Pay-dividends": ["pay", "dividend"],
    "Other-cff": ["financing", "cff"]
}

#check allowed file extention type to accept csv and excel
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'xlsx', 'xls'}

#key part - data cleaning of each column for uploaded file
def clean_data(df):
    try:
        # Convert column names to lowercase
        df.columns = df.columns.str.lower()

        # Check if required columns exist
        required_columns = ['date', 'amount']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"'{col}' column not found in the uploaded file")

        # If 'type' column doesn't exist, add it with a default value
        if 'type' not in df.columns:
            current_app.logger.warning("'type' column not found. Adding it with default value 'Other-cfo'")
            df['type'] = 'Other-cfo'

        # Convert 'date' to datetime, then to string format 'YYYY-MM-DD'
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')

        # Ensure amount is numeric
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        # Log original types
        current_app.logger.info(f"Original types: {df['type'].unique().tolist()}")

        # Validate and map 'type' to allowed types
        def map_type(type_value):
            type_value = str(type_value).lower()
            for allowed_type, keywords in ALLOWED_TYPES.items():
                if any(keyword in type_value for keyword in keywords):
                    return allowed_type
            return "Other-cfo"  # Default to Other-cfo if not recognized

        df['type'] = df['type'].apply(map_type)

        # Log the unique types after mapping
        current_app.logger.info(f"Unique types after mapping: {df['type'].unique().tolist()}")

        # Drop rows with NaN values
        df_cleaned = df.dropna()
        current_app.logger.info(f"Data cleaning complete. Rows before: {len(df)}, Rows after: {len(df_cleaned)}")

        return df_cleaned

    except Exception as e:
        current_app.logger.error(f"Error in clean_data: {str(e)}")
        raise

# csv/excel file upload to temp folder and apply cleaning rules
def process_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError('Unsupported file type')
            
            current_app.logger.info(f"File read successfully. Shape: {df.shape}")
            current_app.logger.info(f"Columns: {df.columns.tolist()}")
            
            cleaned_df = clean_data(df)
            
            return {
                'message': 'File processed successfully',
                'data': cleaned_df.to_dict('records'),
                'columns': cleaned_df.columns.tolist()
            }
        
        except Exception as e:
            current_app.logger.error(f"Error processing file: {str(e)}")
            raise
        
        finally:
            os.remove(file_path)  # Remove the uploaded file after processing
    else:
        raise ValueError('Invalid file type')