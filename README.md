# I Bond Rotation Analyzer

This Python script provides a tool to analyze US Series I Savings Bonds and help determine if it's financially advantageous to redeem ("sell") older bonds and purchase new ones, primarily focusing on capturing a higher *fixed rate* component offered on newer bonds.

It calculates the potential long-term benefit of the higher fixed rate against the immediate costs incurred by selling the old bond (early redemption penalties and federal taxes on accrued interest).

## Features

*   **CSV Input:** Reads I Bond data directly from a CSV file exported or created from your TreasuryDirect holdings (or similar format).
*   **Parameter Driven:** Allows users to input:
    *   The fixed rate of the *new* I Bond series being considered.
    *   Their estimated federal income tax rate.
    *   Their intended investment horizon (how many years they plan to hold the *new* bond).
*   **Detailed Analysis per Bond:** For each bond in the CSV, it calculates:
    *   Bond Age (Years, Months, Total Months)
    *   Applicability of the 3-month interest penalty (if held < 5 years).
    *   Estimated penalty amount (based on current composite rate and value).
    *   Accrued interest subject to tax.
    *   Estimated federal taxes owed upon redemption.
    *   Total immediate cost of selling (penalty + taxes).
    *   Net proceeds available for reinvestment.
    *   Estimated break-even point in years (when the fixed-rate benefit overcomes the immediate costs).
    *   Compounded benefit of the higher fixed rate over the specified investment horizon.
    *   Net financial gain or loss from rotating over the horizon.
*   **Clear Recommendations:** Provides a simple conclusion for each bond (e.g., "CONSIDER ROTATING", "LIKELY DO NOT ROTATE") based on the analysis.
*   **Overall Summary:** Calculates the total number of bonds recommended for rotation and the total estimated net gain across those bonds for the specified horizon.
*   **GUI Interface:** Uses `tkinter` for a user-friendly graphical interface to load the CSV, set parameters, and view results.

## How to Use

1.  **Prepare your CSV:** Create a CSV file (`.csv`) containing your I Bond data. It **must** include the columns specified below. See the example format.
2.  **Install Dependencies:** Ensure you have Python 3 installed. You also need the `python-dateutil` library:
    ```bash
    pip install python-dateutil
    ```
    *Note: `tkinter` is usually included with Python, but on some Linux distributions, you might need to install it separately (e.g., `sudo apt-get install python3-tk`).*
3.  **Run the script:** Execute the Python script from your terminal:
    ```bash
    python i_bond_analysis.py
    ```
4.  **Use the GUI:**
    *   The application window will appear.
    *   Click "Browse..." to select your prepared CSV file.
    *   Enter the "New Bond Fixed Rate (%)", your "Federal Tax Rate (%)", and the desired "Investment Horizon (Years)" into the respective fields.
    *   Click the "Analyze Bonds from CSV" button.
5.  **Review Results:**
    *   Warnings or errors during CSV processing will appear in the main text area.
    *   Select individual bonds from the dropdown menu ("Select Bond to View Details:") to view their detailed analysis in the text area below it.
    *   Check the "Overall Summary" section at the bottom for totals.

## Required CSV Format

The CSV file **must** contain a header row with the following column names (case-sensitive, spacing matters as shown):

*   `Confirmation` : Unique identifier for the bond (can be any text).
*   `Issue Date` : The date the bond was issued, in **YYYY-MM-DD** format (e.g., `2022-05-01`).
*   `Fixed Rate` : The fixed rate percentage assigned to this bond when issued (e.g., `0.0`, `0.2`, `1.3`). **Enter as a percentage number, not a decimal.**
*   `Composite Interest rate` : The *current* composite interest rate percentage applied to the bond (e.g., `4.28`, `5.27`). Used for penalty estimation. **Enter as a percentage number, not a decimal.**
*   `Original amount` : The principal amount of the bond purchase (e.g., `1000.00`, `10000`).
*   `Current Value` : The current redemption value of the bond *before* any penalties (e.g., `1055.50`, `11200.80`).

**Important:** Ensure numeric columns (`Fixed Rate`, `Composite Interest rate`, `Original amount`, `Current Value`) contain only numbers (and potentially a decimal point) and no currency symbols, commas, or percentage signs within the data itself.

## CSV File Example

Here is an example of what the `my_i_bonds.csv` file structure should look like:

```csv
Confirmation,Issue Date,Fixed Rate,Composite Interest rate,Original amount,Current Value
MYBOND001,2003-05-01,1.1,3.94,1000.00,2150.80
MYBOND002,2021-11-01,0.0,4.28,5000.00,5610.00
MYBOND003,2023-02-01,0.4,4.35,10000.00,10552.00
MYBOND004,2023-12-01,1.3,5.27,2500.00,2532.75
EARLY_BOND,2024-03-01,1.3,5.27,1000.00,1000.00


Disclaimers
This tool provides estimations based on the data and parameters you provide.
The early withdrawal penalty calculation is an estimate based on the current composite rate and value provided in the CSV; the actual penalty applied by TreasuryDirect upon redemption may differ slightly. Verify values on TreasuryDirect.
The analysis assumes the calculated "Net Proceeds" are fully reinvested into a new I Bond.
It only considers federal income tax. I Bond interest is typically exempt from state and local income taxes, which is not factored into this calculation.
It does not account for the annual $10,000 purchase limit per SSN for electronic I Bonds.
It does not compare I Bond returns against other potential investments.
Future inflation rates, which affect the variable component of the I Bond composite rate, are unknown and not predicted here. The analysis focuses primarily on the fixed rate difference.
This is not financial advice. Consult with a qualified financial advisor before making any investment decisions based on this tool's output.
