from anthropic import Anthropic
from flask import current_app
import json
import ast

def generate_financial_analysis(initial_balance, current_balance, total_cfo, total_cfi, total_cff, transaction_data):
    api_key = current_app.config.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in the application configuration")
    
    if api_key == 'your-fallback-api-key-here':
        raise ValueError("Please replace the fallback API key with your actual Anthropic API key")
    
    try:
        anthropic = Anthropic(api_key=api_key)
    except Exception as e:
        raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

    prompt = f"""As a financial analyst, provide a concise analysis of the following financial data:

    Initial Balance: ${initial_balance}
    Current Balance: ${current_balance}
    Total CFO: ${total_cfo}
    Total CFI: ${total_cfi}
    Total CFF: ${total_cff}

    Transaction Data:
    {transaction_data}

    Please provide a brief, bullet-point analysis covering:
    - Financial health analysis based on CFO, CFI, and CFF (2-3 points)
    - 30, 60, and 90-day forecast for CFO, CFI, and CFF (compact table format)
    - Projected total balances (compact table format)
    - Key recommendations (2-3 points)

    Limit each bullet point to 20 words or less. Use compact tables where applicable."""

    try:
        message = anthropic.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        current_app.logger.error(f"Error calling Anthropic API: {str(e)}")
        raise

def generate_cashflow_statement(initial_balance, start_date, end_date, transaction_data):
    api_key = current_app.config.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        current_app.logger.error("ANTHROPIC_API_KEY is not set in the application configuration")
        raise ValueError("ANTHROPIC_API_KEY is not set in the application configuration")
    
    try:
        anthropic = Anthropic(api_key=api_key)
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Anthropic client: {str(e)}")
        raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

    prompt = f"""As a financial analyst, generate a detailed cash flow statement based on the following data:

    Initial Balance: ${initial_balance}
    Start Date: {start_date}
    End Date: {end_date}

    Transaction Data:
    {transaction_data}

    Please provide a cash flow statement with the following main categories and subcategories:
    1. Cash flows from Operating Activities (CFO)
       - Cash from customers
       - Cash paid to suppliers and employees
       - Interest paid
       - Income taxes paid
       - Other operating cash flows
    2. Cash flows from Investing Activities (CFI)
       - Purchase of property and equipment
       - Sale of property and equipment
       - Purchase of investments
       - Sale of investments
       - Other investing cash flows
    3. Cash flows from Financing Activities (CFF)
       - Proceeds from issuing shares
       - Proceeds from long-term borrowings
       - Repayment of long-term borrowings
       - Dividends paid
       - Other financing cash flows

    Format your response as a Python list of dictionaries, where each dictionary represents a subcategory in the cash flow statement. Each dictionary should have 'Category', 'Subcategory', and 'Amount' keys. The 'Category' should be one of 'CFO', 'CFI', or 'CFF'. The 'Amount' should be a float value representing the sum for that subcategory.

    Example format:
    [
        {{"Category": "CFO", "Subcategory": "Cash from customers", "Amount": 50000.0}},
        {{"Category": "CFO", "Subcategory": "Cash paid to suppliers and employees", "Amount": -30000.0}},
        {{"Category": "CFI", "Subcategory": "Purchase of property and equipment", "Amount": -5000.0}},
        {{"Category": "CFF", "Subcategory": "Proceeds from long-term borrowings", "Amount": 10000.0}},
    ]

    Ensure that your response can be directly evaluated as a Python list of dictionaries."""

    try:
        current_app.logger.info("Sending request to Anthropic API")
        message = anthropic.messages.create(
            model="claude-3-sonnet-20240620",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        response_text = message.content[0].text
        current_app.logger.info("Received response from Anthropic API")
        current_app.logger.debug(f"Raw API response: {response_text}")
        
        # Parse the response
        statement_data = ast.literal_eval(response_text)

        if not isinstance(statement_data, list):
            raise ValueError("Response is not a list of dictionaries")
        
        for item in statement_data:
            if not isinstance(item, dict) or 'Category' not in item or 'Subcategory' not in item or 'Amount' not in item:
                raise ValueError(f"Invalid item structure in response: {item}")
            if item['Amount'] is None:
                current_app.logger.warning(f"None value found for Amount in item: {item}")
                item['Amount'] = 0.0
            try:
                item['Amount'] = float(item['Amount'])
            except ValueError:
                current_app.logger.warning(f"Invalid Amount value in item: {item}")
                item['Amount'] = 0.0
        
        return statement_data
    except Exception as e:
        current_app.logger.error(f"Error processing API response: {str(e)}")
        current_app.logger.error(f"API response: {response_text}")
        raise ValueError(f"Error processing API response: {str(e)}")