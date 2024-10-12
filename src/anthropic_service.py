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
        raise ValueError("ANTHROPIC_API_KEY is not set in the application configuration")
    
    try:
        anthropic = Anthropic(api_key=api_key)
    except Exception as e:
        raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

    prompt = f"""As a financial expert, generate a detailed cash flow statement based on the following data:

    Initial Balance: ${initial_balance}
    Start Date: {start_date}
    End Date: {end_date}

    Transaction Data:
    {transaction_data}

    Please provide the following:
    1. A categorized breakdown of cash flows (CFO, CFI, CFF) with subcategories.
       Note: Classify bank interest payments under Cash Flow from Financing (CFF), not Cash Flow from Operations (CFO).
    2. Total net cash flow for each category (CFO, CFI, CFF).
    3. Overall net cash flow.
    4. Ending cash balance.

    Present the data in a clear, structured format. Use a simple list format with each item on a new line, like this:

    CFO: Cash from customers: 1000
    CFO: Payments to suppliers: -500
    CFI: Purchase of equipment: -2000
    CFF: Bank loan: 5000
    CFF: Interest paid: -200
    ...

    After listing all items, provide the totals and ending balance in the same format:

    Total CFO: 500
    Total CFI: -2000
    Total CFF: 4800
    Overall Net Cash Flow: 3300
    Ending Cash Balance: 4300

    Ensure all calculations are accurate and consistent with the provided transaction data."""

    try:
        message = anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        response = message.content[0].text

        # Log the complete API response
        current_app.logger.info(f"Complete API response:\n{response}")

        # Parse the response
        statement_data, totals = parse_response(response)

        if not statement_data:
            current_app.logger.error("Failed to parse API response")
            return {'error': 'Parsing failed', 'raw_response': response}, None

        # Calculate ending balance
        ending_balance = totals.get('Ending Cash Balance')
        if ending_balance is None:
            ending_balance = initial_balance + totals.get('Overall Net Cash Flow', 0)

        current_app.logger.info(f"Cash Flow Statement Calculation: {totals}")
        current_app.logger.info(f"Ending Balance: {ending_balance}")

        return statement_data, ending_balance

    except Exception as e:
        current_app.logger.error(f"Error generating cash flow statement: {str(e)}")
        current_app.logger.error(f"Error details: {type(e).__name__}, {str(e)}")
        raise

def parse_response(response):
    lines = response.strip().split('\n')
    statement_data = []
    totals = {}

    for line in lines:
        try:
            if ':' not in line:
                continue
            
            if line.count(':') == 2:  # This is a transaction line
                category, subcategory_and_amount = line.split(':', 1)
                subcategory, amount_str = subcategory_and_amount.rsplit(':', 1)
                
                category = category.strip()
                subcategory = subcategory.strip()
                amount = parse_amount(amount_str)
                
                statement_data.append({
                    'Category': category,
                    'Subcategory': subcategory,
                    'Amount': amount
                })
            elif line.count(':') == 1:  # This is a total line
                key, value_str = line.split(':')
                key = key.strip()
                value = parse_amount(value_str)
                totals[key] = value
        except Exception as e:
            current_app.logger.warning(f"Error parsing line '{line}': {str(e)}")

    if not statement_data:
        current_app.logger.error("No valid statement data found in response")
    if not totals:
        current_app.logger.error("No valid totals found in response")

    return statement_data, totals

def parse_amount(amount_str):
    try:
        return float(amount_str.replace('$', '').replace(',', '').strip())
    except ValueError:
        current_app.logger.warning(f"Could not parse amount: {amount_str}")
        return 0.0