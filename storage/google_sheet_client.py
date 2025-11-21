import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetsClient:
    def __init__(self, credentials_path: str, spreadsheet_name: str, worksheet_name: str = "Sheet1"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        client = gspread.authorize(creds)

        self.spreadsheet = client.open(spreadsheet_name)
        self.worksheet = self.spreadsheet.worksheet(worksheet_name)

    def append_row(self, row: list):
        self.worksheet.append_row(row, value_input_option="USER_ENTERED")