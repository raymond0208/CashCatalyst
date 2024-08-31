def calculate_totals(transactions):
    cfo_types = ["Cash-customer", "Salary-suppliers", "Interest-paid", "Income-tax", "Other-cfo"]
    cfi_types = ["Buy-property-equipments", "Sell-property-equipments", "Buy-investment", "Sell-investment", "Other-cfi"]
    cff_types = ["Issue-shares", "borrowings", "Repay-borrowings", "Pay-dividends", "Other-cff"]

    total_cfo = sum(t.amount for t in transactions if t.type in cfo_types)
    total_cfi = sum(t.amount for t in transactions if t.type in cfi_types)
    total_cff = sum(t.amount for t in transactions if t.type in cff_types)

    return total_cfo, total_cfi, total_cff