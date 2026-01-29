"""Spreadsheet Processing Module"""

import pandas as pd
from typing import Optional


class SpreadsheetProcessor:
    """Process spreadsheet files"""
    
    @staticmethod
    def load_file(file) -> Optional[pd.DataFrame]:
        """Load spreadsheet from file"""
        try:
            if file.name.endswith('.csv'):
                return pd.read_csv(file)
            else:
                return pd.read_excel(file)
        except Exception as e:
            raise ValueError(f"Error loading spreadsheet: {str(e)}")
    
    @staticmethod
    def split_string(text, separator=' ', max_len=50) -> list[str]:
        words = text.split(separator)
        parts = []
        current = ""

        for word in words:
            # If adding this word exceeds limit, push current and start new chunk
            if len(current) + len(word) + (1 if current else 0) > max_len:
                parts.append(current)
                current = word
            else:
                current = word if not current else current + " " + word

        # Append last part if non-empty
        if current:
            parts.append(current)

        return parts
    
    # Extract state from the 'Correspondence address' column using malaysia_states list
    @staticmethod
    def extract_state(address) -> Optional[str]:

        malaysia_states = [
            "JOHOR",
            "KEDAH",
            "KELANTAN",
            "MELAKA",
            "NEGERI SEMBILAN",
            "PAHANG",
            "PULAU PINANG",
            "PERAK",
            "PERLIS",
            "SABAH",
            "SARAWAK",
            "SELANGOR",
            "TERENGGANU",
            "WILAYAH PERSEKUTUAN KUALA LUMPUR",
            "WILAYAH PERSEKUTUAN PUTRAJAYA",
            "WILAYAH PERSEKUTUAN LABUAN"
        ]

        for state in malaysia_states:
            if state in address:
                return state
        return None
    
    @staticmethod
    # Extract city by removing address_line_1, postcode, and state from 'Correspondence address'
    def extract_city(row) -> Optional[str]:
        address = row['Correspondence address']
        address_line = row['address_line']
        postcode = row['postcode']
        state = row['state']
        if address_line and postcode and state:
            return address.replace(address_line, '').replace(postcode, '').replace(state, '').strip()
        return None
    
    @staticmethod
    def process_file(df: pd.DataFrame) -> pd.DataFrame:
        """Process spreadsheet data"""

        employer_category_map = {
            'GOVERNTMENT': '1',
            'STATUTORY': '2',
            'LOCAL AUTHORITY': '3',
            'PRIVATE SECTOR - COMPANY': '4',
            'PRIVATE SECTOR - OTHER THAN COMPANY': '5',
            'SPECIAL CLASS EMPLOYER': '6'
            }

        employer_status_map = {
            'IN OPERATION': '1',
            'DORMANT': '2',
            'IN THE PROCESS OF WINDING UP': '3'
            }

        tin_code_map = {
            'IG': '01',
            'D': '02',
            'C': '03',
            'J': '04',
            'F': '05',
            'TP': '06',
            'TA': '07',
            'TC': '08',
            'CS': '09',
            'TR': '10',
            'PT': '11',
            'TN': '12',
            'LE': '13'
        }

        furnish_cp8d_map = {
            'VIA e-DATA Praisi / e-CP8D': '1',
            'Exempted': '2'
        }

        # Remove leading/trailing whitespace from all column names
        df.columns = df.columns.str.strip()

        # Rename column if misnamed
        if 'Name Of Employee As Registered' in df.columns:
            df = df.rename(columns={'Name Of Employee As Registered': 'Name Of Employer As Registered'})

        # Convert first column to uppercase
        df.loc[:, 'Name Of Employer As Registered'] = df.loc[:, 'Name Of Employer As Registered'].str.upper()

        # Split employer name if exceeds 50 characters
        df.loc[:, 'employer_name_split'] = df.loc[:, 'Name Of Employer As Registered'].str.upper().apply(lambda x: SpreadsheetProcessor.split_string(x, max_len=52))

        # Create new columns for split employer names
        df.loc[:, 'Name Of Employer As Registered 1'] = df['employer_name_split'].apply(lambda x: x[0])
        df.loc[:, 'Name Of Employer As Registered 2'] = df['employer_name_split'].apply(lambda x: x[1] if len(x) > 1 else '')
        df.loc[:, 'Name Of Employer As Registered 3'] = df['employer_name_split'].apply(lambda x: x[2] if len(x) > 2 else '')

        # Extract only digits from the 'Employer's TIN' column
        df.loc[:, "Employer's TIN"] = df.loc[:, "Employer's TIN"].str.extract('(\d+)', expand=False)

        # Extract TIN code from the 'Tax Identification No (TIN)' column (letters only)
        df.loc[:, "TIN Code"] = df.loc[:, "Tax Identification No (TIN)"].str.extract('([A-Z]+)', expand=False)
        
        # Extract TIN number from the 'Tax Identification No (TIN)' column (digits only)
        df.loc[:, "TIN Number"] = df.loc[:, "Tax Identification No (TIN)"].str.extract('(\d+)', expand=False)

        df['Category Of Employer'] = df['Category Of Employer'].replace(employer_category_map)
        df['Employer Status'] = df['Employer Status'].replace(employer_status_map)
        df['TIN Code'] = df['TIN Code'].replace(tin_code_map)
        df['Furnish of C.P.8D'] = df['Furnish of C.P.8D'].replace(furnish_cp8d_map)

        df['country'] = 'MALAYSIA'

        # Extract 5-digit postcode
        df['postcode'] = df['Correspondence address'].str.extract(r'(\b\d{5}\b)', expand=False)

        # Extract address line 1 before the 5-digit postcode
        df['address_line'] = df['Correspondence address'].str.extract(r'^(.*?)(?=\b\d{5}\b)', expand=False).str.strip()

        # Split correspondence address if exceeds 62 characters
        df.loc[:, 'address_line_split'] = df.loc[:, 'address_line'].str.upper().apply(lambda x: SpreadsheetProcessor.split_string(x, separator=',', max_len=62))

        # Create new columns for split correspondence addresses
        df.loc[:, 'address_line_1'] = df['address_line_split'].apply(lambda x: x[0].replace('  ', ', '))
        df.loc[:, 'address_line_2'] = df['address_line_split'].apply(lambda x: x[1].replace('  ', ', ') if len(x) > 1 else '')
        df.loc[:, 'address_line_3'] = df['address_line_split'].apply(lambda x: x[2].replace('  ', ', ') if len(x) > 2 else '')

        # Correct 'PERSEKETUAN' to 'PERSEKUTUAN' in state names
        df['Correspondence address'] = df['Correspondence address'].replace('PERSEKETUAN', 'PERSEKUTUAN', regex=True)
        
        # Extract state from the 'Correspondence address' column
        df['state'] = df['Correspondence address'].apply(SpreadsheetProcessor.extract_state)

        # Extract city from the 'Correspondence address' column
        df['city'] = df.apply(SpreadsheetProcessor.extract_city, axis=1)

        # Abbreviate 'WILAYAH PERSEKUTUAN' to 'WP'
        df['state'] = df['state'].str.replace('WILAYAH PERSEKUTUAN', 'WP')
        
        # Rename (remove newline characters)
        df.columns = df.columns.str.replace('\n', ' ')

        # Subset relevant columns only
        df = df[[
            'Name Of Employer As Registered 1',
            'Name Of Employer As Registered 2',
            'Name Of Employer As Registered 3',
            "Employer's TIN",
            'Category Of Employer',
            'Employer Status',
            'TIN Code',
            'TIN Number',
            'Registration no. with Companies Commission of Malaysia (CCM) or others',
            'address_line_1',
            'address_line_2',
            'address_line_3',
            'postcode',
            'city',
            'state',
            'country',
            'Telephone no.',
            'e-Mail',
            'Furnish of C.P.8D',
            'Number of employees as at 31/12/2025',
            'Number of employees subjected to Monthly Tax Deduction (MTD)',
            'Number of new employees',
            'Number of employees who ceased employed / died',
            'Number of employees who ceased employment and left Malaysia',
            'Reported to LHDNM (If No. 5 is applicable)'
        ]]

        return df