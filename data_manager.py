import pandas as pd
import datetime
import os

class DataManager:
    def __init__(self, file_path="portfolio.xlsx", use_google_sheets=False, google_sheet_name=None, google_wks_key=None):
        self.file_path = file_path
        self.use_google_sheets = use_google_sheets
        # Placeholder for Google Sheets initialization
        if self.use_google_sheets:
            print("Google Sheets integration not yet implemented. Using local file.")
            self.use_google_sheets = False 

    def load_portfolio(self):
        """Loads the 'Portfolio' sheet."""
        if self.use_google_sheets:
            # TODO: Implement gspread loading
            pass
        else:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"{self.file_path} not found.")
            # Read 'Ticker' as string to preserve leading zeros
            return pd.read_excel(self.file_path, sheet_name='Portfolio', dtype={'Ticker': str}, engine='openpyxl')

    def load_history(self):
        """Loads the 'History' sheet."""
        if self.use_google_sheets:
            # TODO: Implement gspread loading
            pass
        else:
            if not os.path.exists(self.file_path):
                # Return empty dataframe if file/sheet doesn't exist
                return pd.DataFrame(columns=['Date', 'Total_Asset', 'Profit_Rate', 'Memo'])
            try:
                return pd.read_excel(self.file_path, sheet_name='History', engine='openpyxl')
            except ValueError:
                # Sheet might not exist
                 return pd.DataFrame(columns=['Date', 'Total_Asset', 'Profit_Rate', 'Memo'])

    def append_history(self, date, total_asset, profit_rate, memo=""):
        """Appends a new record to the 'History' sheet."""
        new_row = pd.DataFrame([{
            'Date': date,
            'Total_Asset': total_asset,
            'Profit_Rate': profit_rate,
            'Memo': memo
        }])

        if self.use_google_sheets:
            # TODO: Implement gspread appending
            pass
        else:
            if not os.path.exists(self.file_path):
                 raise FileNotFoundError(f"{self.file_path} not found.")
            
            # Load existing history
            try:
                current_history = pd.read_excel(self.file_path, sheet_name='History', engine='openpyxl')
            except ValueError:
                current_history = pd.DataFrame(columns=['Date', 'Total_Asset', 'Profit_Rate', 'Memo'])
            
            updated_history = pd.concat([current_history, new_row], ignore_index=True)
            
            # We need to write back both sheets to preserve the Portfolio sheet. 
            # This is a limitation of pandas to_excel, it overwrites the file.
            # We must load portfolio first.
            portfolio_df = self.load_portfolio()
            
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                portfolio_df.to_excel(writer, sheet_name='Portfolio', index=False)
                updated_history.to_excel(writer, sheet_name='History', index=False)
            
            print(f"Appended history: {date} - {total_asset}")

# Simple test
if __name__ == "__main__":
    dm = DataManager()
    print("Portfolio:", dm.load_portfolio().head())
    print("History:", dm.load_history().head())
    # dm.append_history(datetime.date.today().isoformat(), 20000000, 0.05, "Test Run")
