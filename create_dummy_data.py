import pandas as pd
import os

# Define the file path
file_path = r"d:\★사용자 폴더\Documents\port\portfolio_tracker\portfolio.xlsx"

# Data for 'Portfolio' sheet
portfolio_data = {
    'Ticker': ['360750', '456780', '005930', 'SPY'],
    'Name': ['TIGER 글로벌리튬&2차전지SOLACTIVE(합성)', 'ACE 애플밸류체인Active', '삼성전자', 'SPDR S&P 500 ETF Trust'],
    'Category': ['Theme', 'Theme', 'Domestic', 'US Market'],
    'Quantity': [85.72653, 298.8439, 10, 5],
    'Target_Weight': [0.1, 0.3, 0.2, 0.4]
}
portfolio_df = pd.DataFrame(portfolio_data)

# Data for 'History' sheet (Initial empty structure with one row for checking)
history_data = {
    'Date': ['2023-01-01'],
    'Total_Asset': [10000000],
    'Profit_Rate': [0.0],
    'Memo': ['Initial Setup']
}
history_df = pd.DataFrame(history_data)

# Create the Excel file with two sheets
with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
    portfolio_df.to_excel(writer, sheet_name='Portfolio', index=False)
    history_df.to_excel(writer, sheet_name='History', index=False)

print(f"Created {file_path}")
