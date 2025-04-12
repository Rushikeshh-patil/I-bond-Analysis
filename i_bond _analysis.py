import sys
import math
import csv
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import tkinter as tk
from tkinter import ttk, messagebox # Import messagebox for potential errors
from tkinter import filedialog
from tkinter import scrolledtext
import os # To get default path

# --- Default Values (Used for GUI initialization) ---
DEFAULT_NEW_BOND_FIXED_RATE_PCT = 1.3
DEFAULT_FEDERAL_TAX_RATE_PCT = 22.0
DEFAULT_INVESTMENT_HORIZON_YEARS = 10
# --- CSV File Configuration ---
CSV_COL_CONFIRMATION = 'Confirmation'
CSV_COL_ISSUE_DATE = 'Issue Date'
CSV_COL_FIXED_RATE = 'Fixed Rate'
CSV_COL_COMPOSITE_RATE = 'Composite Interest rate'
CSV_COL_PRINCIPAL = 'Original amount'
CSV_COL_CURRENT_VALUE = 'Current Value'

# --- Core Calculation Logic (Unchanged) ---
def calculate_rotation_metrics(
    old_bond_principal,
    old_bond_issue_date,
    old_bond_fixed_rate_pct,
    old_bond_current_value,
    old_bond_composite_rate_pct,
    new_bond_fixed_rate_pct,
    federal_tax_rate_pct,
    investment_horizon_years
):
    """Calculates rotation metrics for a single bond. Returns a dictionary of results."""
    # --- [This function remains exactly the same as the previous version] ---
    # --- [Ensure the full calculate_rotation_metrics function body is here] ---
    results = {} # Dictionary to store results

    # --- Input Validation (Basic checks on provided values) ---
    if old_bond_current_value < old_bond_principal:
        results['warning'] = "Current value is less than principal. Check inputs."
    else:
        results['warning'] = None

    if new_bond_fixed_rate_pct <= old_bond_fixed_rate_pct:
         results['note'] = f"New fixed rate ({new_bond_fixed_rate_pct}%) is not higher than this bond's rate ({old_bond_fixed_rate_pct}%)."
    else:
        results['note'] = None

    # --- Convert Percentages to Decimals ---
    try:
        old_fixed_rate = old_bond_fixed_rate_pct / 100.0
        old_composite_rate = old_bond_composite_rate_pct / 100.0
        new_fixed_rate = new_bond_fixed_rate_pct / 100.0
        tax_rate = federal_tax_rate_pct / 100.0
    except TypeError:
        results['error'] = "Invalid non-numeric rate/percentage detected."
        return results

    # --- Calculate Bond Age ---
    today = date.today()
    try:
        # Ensure old_bond_issue_date is a date object
        if not isinstance(old_bond_issue_date, date):
             # Attempt conversion if it's a string (should be date object already)
             if isinstance(old_bond_issue_date, str):
                 old_bond_issue_date = datetime.strptime(old_bond_issue_date, '%Y-%m-%d').date()
             else:
                 raise TypeError("Issue date is not a valid date object or string.")
        delta = relativedelta(today, old_bond_issue_date)
        bond_age_years = delta.years
        bond_age_months = delta.months
        total_months_held = bond_age_years * 12 + bond_age_months
        results['age_str'] = f"{bond_age_years} years, {bond_age_months} months ({total_months_held} total months)"
        results['total_months_held'] = total_months_held
    except Exception as e:
        results['error'] = f"Could not calculate age from issue date {old_bond_issue_date}: {e}"
        return results # Stop calculation for this bond

    # --- Check Minimum Holding Period ---
    if total_months_held < 12:
        results['error'] = "Cannot be redeemed (held less than 12 months)."
        # Don't return yet, still useful to show other info like age
        results['penalty_applies'] = False # No penalty if cannot redeem
        results['penalty'] = 0.0
        results['accrued_interest'] = max(0, old_bond_current_value - old_bond_principal)
        results['taxes_owed'] = results['accrued_interest'] * tax_rate
        results['immediate_cost'] = results['taxes_owed'] # No penalty applicable
        results['net_proceeds'] = old_bond_current_value - results['immediate_cost']
        results['compounded_fixed_rate_benefit'] = 0.0 # Cannot rotate
        results['net_gain_or_loss'] = 0.0 # Cannot rotate
        results['break_even_years'] = -1 # Not applicable
        return results


    # --- Calculate Early Withdrawal Penalty ---
    penalty = 0.0
    penalty_applies = False
    if total_months_held < 60: # Less than 5 years (5 * 12 = 60 months)
        penalty_applies = True
        # Estimate penalty: 3 months interest based on the *current* composite rate
        three_months_interest = old_bond_current_value * (old_composite_rate / 4.0)
        penalty = three_months_interest
    results['penalty_applies'] = penalty_applies
    results['penalty'] = penalty

    # --- Calculate Accrued Interest & Taxes ---
    accrued_interest = max(0, old_bond_current_value - old_bond_principal) # Ensure non-negative
    taxes_owed = accrued_interest * tax_rate
    results['accrued_interest'] = accrued_interest
    results['taxes_owed'] = taxes_owed

    # --- Calculate Costs and Net Proceeds ---
    immediate_cost = penalty + taxes_owed
    net_proceeds = old_bond_current_value - immediate_cost
    results['immediate_cost'] = immediate_cost
    results['net_proceeds'] = net_proceeds

    if net_proceeds <= 0:
         results['error'] = "Calculated Net Proceeds are zero or negative after costs. Rotation not possible/sensible."
         results['compounded_fixed_rate_benefit'] = 0.0
         results['net_gain_or_loss'] = -immediate_cost # Net loss is the cost itself
         results['break_even_years'] = -1
         return results # Stop calculation

    # --- Calculate Compounded Benefit of Fixed Rate Difference (over specified horizon) ---
    try:
        # Ensure horizon is positive integer
        if not isinstance(investment_horizon_years, int) or investment_horizon_years <= 0:
             raise ValueError("Investment horizon must be a positive integer.")

        fv_new_fixed = net_proceeds * math.pow((1 + new_fixed_rate), investment_horizon_years)
        fv_old_fixed = net_proceeds * math.pow((1 + old_fixed_rate), investment_horizon_years)
        compounded_fixed_rate_benefit = fv_new_fixed - fv_old_fixed
        results['compounded_fixed_rate_benefit'] = compounded_fixed_rate_benefit
    except OverflowError:
         results['error'] = "Calculation resulted in overflow (likely very large horizon or rates)."
         return results
    except ValueError as ve:
         results['error'] = f"Math domain error during compounding: {ve} (check rates/horizon)."
         return results


    # --- Compare Benefit vs. Cost (over specified horizon) ---
    net_gain_or_loss = compounded_fixed_rate_benefit - immediate_cost
    results['net_gain_or_loss'] = net_gain_or_loss

    # --- Calculate Break-Even Point ---
    break_even_years = -1
    max_years_to_check = 100
    if immediate_cost > 0 and new_fixed_rate > old_fixed_rate:
        try:
            cumulative_benefit = 0.0
            for year in range(1, max_years_to_check + 1):
                fv_new = net_proceeds * math.pow((1 + new_fixed_rate), year)
                fv_old = net_proceeds * math.pow((1 + old_fixed_rate), year)
                cumulative_benefit = fv_new - fv_old
                if cumulative_benefit >= immediate_cost:
                    break_even_years = year
                    break
        except (OverflowError, ValueError):
             break_even_years = -2 # Indicate calculation issue
    elif immediate_cost <= 0 and new_fixed_rate > old_fixed_rate:
         break_even_years = 0 # No cost to recoup, benefit starts immediately if rate is higher
    results['break_even_years'] = break_even_years
    results['max_years_to_check'] = max_years_to_check

    results['error'] = None # No error if calculation completes this far
    return results
# --- [End of calculate_rotation_metrics function body] ---


# --- GUI Application Class ---
class IBondAnalyzerApp:
    def __init__(self, master):
        self.master = master
        master.title("I Bond Rotation Analyzer")
        master.geometry("800x750") # Increased size slightly

        # --- Data Storage ---
        self.analysis_results = {} # Stores {confirmation: {'metrics': metrics_dict, 'input': bond_input_dict}}
        self.bond_confirmations = [] # List to populate dropdown

        # --- Variables for input fields ---
        self.csv_filepath = tk.StringVar()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_csv = os.path.join(script_dir, 'my_i_bonds.csv')
        self.csv_filepath.set(default_csv)

        self.new_rate_var = tk.DoubleVar(value=DEFAULT_NEW_BOND_FIXED_RATE_PCT)
        self.tax_rate_var = tk.DoubleVar(value=DEFAULT_FEDERAL_TAX_RATE_PCT)
        self.horizon_var = tk.IntVar(value=DEFAULT_INVESTMENT_HORIZON_YEARS)

        # --- Create Widgets ---
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="10 10 10 10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1) # Allow main frame to expand

        # --- Input Parameter Section (Row 0) ---
        input_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="10")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(1, weight=1)
        # (Widgets inside input_frame remain the same as before)
        ttk.Label(input_frame, text="CSV File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        csv_entry = ttk.Entry(input_frame, textvariable=self.csv_filepath, width=60)
        csv_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        browse_button = ttk.Button(input_frame, text="Browse...", command=self.browse_file)
        browse_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=2)
        ttk.Label(input_frame, text="New Bond Fixed Rate (%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        new_rate_entry = ttk.Entry(input_frame, textvariable=self.new_rate_var, width=10)
        new_rate_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(input_frame, text="Federal Tax Rate (%):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        tax_rate_entry = ttk.Entry(input_frame, textvariable=self.tax_rate_var, width=10)
        tax_rate_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(input_frame, text="Investment Horizon (Years):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        horizon_entry = ttk.Entry(input_frame, textvariable=self.horizon_var, width=10)
        horizon_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)


        # --- Action Button (Row 1) ---
        analyze_button = ttk.Button(main_frame, text="Analyze Bonds from CSV", command=self.run_analysis)
        analyze_button.grid(row=1, column=0, columnspan=2, pady=10)

        # --- Results Display Area (Row 2) ---
        results_area_frame = ttk.Frame(main_frame)
        results_area_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(2, weight=1) # Allow results area to expand vertically
        results_area_frame.columnconfigure(0, weight=1) # Allow results area to expand horizontally

        # Dropdown Selection
        select_frame = ttk.Frame(results_area_frame)
        select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        select_frame.columnconfigure(1, weight=1)
        ttk.Label(select_frame, text="Select Bond to View Details:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.bond_selector = ttk.Combobox(select_frame, values=self.bond_confirmations, state="readonly", width=40)
        self.bond_selector.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.bond_selector.bind("<<ComboboxSelected>>", self.on_bond_select)

        # Detailed Results Text Area
        detail_frame = ttk.LabelFrame(results_area_frame, text="Selected Bond Details", padding="10")
        detail_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_area_frame.rowconfigure(1, weight=1) # Allow detail frame to expand
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)

        self.detail_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, width=80, height=18, state=tk.DISABLED)
        self.detail_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Summary Section (Row 3) ---
        summary_frame = ttk.LabelFrame(main_frame, text="Overall Summary", padding="10")
        summary_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        summary_frame.columnconfigure(1, weight=1)

        ttk.Label(summary_frame, text="Bonds Recommended for Rotation:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.summary_count_var = tk.StringVar(value="N/A")
        ttk.Label(summary_frame, textvariable=self.summary_count_var).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(summary_frame, text="Total Estimated Net Gain (Horizon):").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.summary_gain_var = tk.StringVar(value="N/A")
        ttk.Label(summary_frame, textvariable=self.summary_gain_var).grid(row=1, column=1, sticky=tk.W, padx=5)

        # --- Status Bar (Row 4) ---
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5,0))


    def browse_file(self):
        """Opens a file dialog to select a CSV file."""
        filepath = filedialog.askopenfilename(
            title="Select I Bond CSV File",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filepath:
            self.csv_filepath.set(filepath)
            self.status_var.set(f"Selected file: {os.path.basename(filepath)}")

    def _clear_results(self):
        """Clears previous analysis results from GUI elements."""
        self.analysis_results = {}
        self.bond_confirmations = []
        self.bond_selector['values'] = []
        self.bond_selector.set('')
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete('1.0', tk.END)
        self.detail_text.config(state=tk.DISABLED)
        self.summary_count_var.set("N/A")
        self.summary_gain_var.set("N/A")

    def _log_to_details(self, message):
        """Appends a message to the detail results text area."""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.insert(tk.END, message + "\n")
        self.detail_text.config(state=tk.DISABLED)
        self.detail_text.see(tk.END) # Scroll to the end
        self.master.update_idletasks() # Ensure GUI updates

    def _format_bond_details(self, confirmation):
        """Formats the analysis results for a single bond into a string."""
        if confirmation not in self.analysis_results:
            return "Error: Results not found for this bond."

        data = self.analysis_results[confirmation]
        metrics = data['metrics']
        bond = data['input']
        federal_tax_rate_pct = data['tax_rate_used'] # Get the rate used for this analysis
        investment_horizon_years = data['horizon_used'] # Get the horizon used

        lines = []
        lines.append(f"--- Details for Bond (Conf: {confirmation}) ---")
        lines.append(f"    (Issued: {bond['issue_date']}, Fixed Rate: {bond['fixed_rate_pct']}%)")
        lines.append(f"    (Principal: ${bond['principal']:,.2f}, Current Value: ${bond['current_value']:,.2f})")

        analysis_error = metrics.get('error')

        if metrics.get('warning'): lines.append(f"\nInput Warning: {metrics['warning']}")
        if metrics.get('note'): lines.append(f"Note: {metrics['note']}")

        lines.append(f"\nBond Age: {metrics.get('age_str', 'N/A')}")

        if analysis_error == "Cannot be redeemed (held less than 12 months).":
             lines.append(f"Status: {analysis_error}")
             lines.append(f"Accrued Interest: ${metrics.get('accrued_interest', 0):,.2f}")
             lines.append(f"Estimated Federal Taxes Owed (if redeemed later): ${metrics.get('taxes_owed', 0):,.2f}")
             lines.append("-" * 25)
             lines.append("Conclusion: Cannot rotate now.")
             return "\n".join(lines)

        if analysis_error:
            lines.append(f"\nAnalysis Error: {analysis_error}")
            return "\n".join(lines)

        # Display normal results
        if metrics.get('penalty_applies'):
            lines.append(f"Penalty Applies (Held < 5 years): YES")
            lines.append(f"  Estimated Penalty: ${metrics.get('penalty', 0):,.2f}")
        else:
            lines.append(f"Penalty Applies (Held >= 5 years): NO")
            lines.append(f"  Estimated Penalty: $0.00")

        lines.append(f"Accrued Interest: ${metrics.get('accrued_interest', 0):,.2f}")
        lines.append(f"Estimated Federal Taxes Owed (at {federal_tax_rate_pct:.1f}%): ${metrics.get('taxes_owed', 0):,.2f}")
        lines.append(f"Total Immediate Cost of Selling: ${metrics.get('immediate_cost', 0):,.2f}")
        lines.append(f"Net Proceeds to Reinvest: ${metrics.get('net_proceeds', 0):,.2f}")
        lines.append("-" * 25)
        lines.append(f"Analysis for {investment_horizon_years}-Year Horizon:")

        be_years = metrics.get('break_even_years', -1)
        max_be_check = metrics.get('max_years_to_check', 100)
        if be_years == 0: lines.append(f"Estimated Break-Even Point: Immediate (Year 0)")
        elif be_years > 0: lines.append(f"Estimated Break-Even Point: Approx. {be_years} years")
        elif be_years == -2: lines.append(f"Estimated Break-Even Point: Could not calculate accurately.")
        elif metrics.get('new_rate_used', 0) <= bond['fixed_rate_pct'] and metrics.get('immediate_cost', 0) > 0 :
             lines.append(f"Estimated Break-Even Point: Not applicable (New fixed rate not higher)")
        elif metrics.get('immediate_cost', 0) > 0:
             lines.append(f"Estimated Break-Even Point: Not reached within {max_be_check} years.")
        else: lines.append(f"Estimated Break-Even Point: Not applicable (No cost, new rate not higher)")

        lines.append(f"Compounded Benefit from Higher Fixed Rate: ${metrics.get('compounded_fixed_rate_benefit', 0):,.2f}")
        lines.append(f"Net Financial Gain/(Loss) from Rotation: ${metrics.get('net_gain_or_loss', 0):,.2f}")
        lines.append("-" * 25)

        # Conclusion
        lines.append("Conclusion for this Bond:")
        net_gain_loss = metrics.get('net_gain_or_loss', 0)
        if net_gain_loss > 0:
            lines.append("  >> CONSIDER ROTATING: Potential net GAIN over horizon.")
            if be_years > 0 and investment_horizon_years < be_years:
                 lines.append(f"     (Note: Horizon {investment_horizon_years} yrs is SHORTER than break-even {be_years} yrs)")
            elif be_years > 0 and investment_horizon_years >= be_years:
                 lines.append(f"     (Note: Horizon {investment_horizon_years} yrs is LONGER than/equal to break-even {be_years} yrs)")
        elif net_gain_loss < 0:
             lines.append("  >> LIKELY DO NOT ROTATE: Potential net LOSS over horizon.")
             if bond['fixed_rate_pct'] >= metrics.get('new_rate_used', 0):
                 lines.append("     (Reason: New fixed rate isn't higher)")
             elif metrics.get('immediate_cost', 0) > metrics.get('compounded_fixed_rate_benefit', 0):
                 lines.append("     (Reason: Immediate costs outweigh fixed-rate benefit)")
        else:
            lines.append("  >> NEUTRAL: Estimated benefits roughly equal costs over horizon.")

        return "\n".join(lines)


    def on_bond_select(self, event=None):
        """Handles the selection change in the bond dropdown."""
        selected_confirmation = self.bond_selector.get()
        if not selected_confirmation:
            return # Nothing selected

        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete('1.0', tk.END)
        details_string = self._format_bond_details(selected_confirmation)
        self.detail_text.insert('1.0', details_string)
        self.detail_text.config(state=tk.DISABLED)
        self.status_var.set(f"Displaying details for {selected_confirmation}")


    def run_analysis(self):
        """Reads the CSV, performs calculations, stores results, and updates GUI."""
        self._clear_results() # Clear previous results first
        self.status_var.set("Starting analysis...")

        # --- Get parameters from GUI ---
        csv_filename = self.csv_filepath.get()
        try:
            new_bond_fixed_rate_pct = self.new_rate_var.get()
            federal_tax_rate_pct = self.tax_rate_var.get()
            investment_horizon_years = self.horizon_var.get()

            if new_bond_fixed_rate_pct < 0 or federal_tax_rate_pct < 0:
                 raise ValueError("Rates cannot be negative.")
            if investment_horizon_years <= 0:
                 raise ValueError("Horizon must be a positive integer.")

        except tk.TclError:
            messagebox.showerror("Input Error", "Invalid numeric input for Rate or Horizon.")
            self.status_var.set("Error: Invalid input.")
            return
        except ValueError as ve:
             messagebox.showerror("Input Error", f"Invalid input value: {ve}")
             self.status_var.set("Error: Invalid input.")
             return

        # --- Read and Process CSV ---
        temp_warnings = [] # Store warnings during processing
        try:
            self.status_var.set(f"Reading CSV: {os.path.basename(csv_filename)}...")
            with open(csv_filename, mode='r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    messagebox.showerror("CSV Error", f"CSV file '{os.path.basename(csv_filename)}' appears to be empty or has no header.")
                    self.status_var.set("Error: Empty or headerless CSV.")
                    return

                required_cols = {
                    CSV_COL_CONFIRMATION, CSV_COL_ISSUE_DATE, CSV_COL_FIXED_RATE,
                    CSV_COL_COMPOSITE_RATE, CSV_COL_PRINCIPAL, CSV_COL_CURRENT_VALUE
                }
                actual_cols = set(map(str.strip, reader.fieldnames))
                if not required_cols.issubset(actual_cols):
                    missing = required_cols - actual_cols
                    messagebox.showerror("CSV Error", f"CSV file '{os.path.basename(csv_filename)}' is missing required columns: {', '.join(missing)}")
                    self.status_var.set("Error: Missing CSV columns.")
                    return

                line_num = 1
                for row in reader:
                    line_num += 1
                    try:
                        confirmation_num = row[CSV_COL_CONFIRMATION].strip()
                        if not confirmation_num: # Skip rows with blank confirmation
                             temp_warnings.append(f"Skipping CSV line {line_num}: Blank confirmation number.")
                             continue

                        issue_date_str = row[CSV_COL_ISSUE_DATE].strip()
                        fixed_rate_str = row[CSV_COL_FIXED_RATE].strip()
                        composite_rate_str = row[CSV_COL_COMPOSITE_RATE].strip()
                        principal_str = row[CSV_COL_PRINCIPAL].strip()
                        current_value_str = row[CSV_COL_CURRENT_VALUE].strip()

                        bond_input = {
                            "confirmation": confirmation_num,
                            "issue_date": datetime.strptime(issue_date_str, '%Y-%m-%d').date(),
                            "fixed_rate_pct": float(fixed_rate_str),
                            "composite_rate_pct": float(composite_rate_str),
                            "principal": float(principal_str),
                            "current_value": float(current_value_str),
                            "csv_line": line_num
                        }

                        if bond_input["fixed_rate_pct"] < 0 or \
                           bond_input["composite_rate_pct"] < 0 or \
                           bond_input["principal"] < 0 or \
                           bond_input["current_value"] < 0:
                            temp_warnings.append(f"Skipping CSV line {line_num} (Conf: {confirmation_num}): Negative numeric value(s).")
                            continue
                        if bond_input["issue_date"] > date.today():
                            temp_warnings.append(f"Skipping CSV line {line_num} (Conf: {confirmation_num}): Future issue date.")
                            continue

                        # Calculate metrics
                        metrics = calculate_rotation_metrics(
                            old_bond_principal=bond_input['principal'],
                            old_bond_issue_date=bond_input['issue_date'],
                            old_bond_fixed_rate_pct=bond_input['fixed_rate_pct'],
                            old_bond_current_value=bond_input['current_value'],
                            old_bond_composite_rate_pct=bond_input['composite_rate_pct'],
                            new_bond_fixed_rate_pct=new_bond_fixed_rate_pct,
                            federal_tax_rate_pct=federal_tax_rate_pct,
                            investment_horizon_years=investment_horizon_years
                        )
                        # Store rates used with metrics for later display
                        metrics['new_rate_used'] = new_bond_fixed_rate_pct

                        # Store results keyed by confirmation number
                        self.analysis_results[confirmation_num] = {
                            'metrics': metrics,
                            'input': bond_input,
                            'tax_rate_used': federal_tax_rate_pct, # Store params used
                            'horizon_used': investment_horizon_years
                        }
                        self.bond_confirmations.append(confirmation_num)


                    except ValueError as ve:
                        temp_warnings.append(f"Skipping CSV line {line_num} (Conf: {confirmation_num}): Data conversion error - {ve}.")
                    except KeyError as ke:
                        temp_warnings.append(f"Skipping CSV line {line_num} (Conf: {confirmation_num}): Missing column key '{ke}'.")
                    except Exception as e:
                        temp_warnings.append(f"Skipping CSV line {line_num} (Conf: {confirmation_num}): Unexpected error - {e}.")

        except FileNotFoundError:
            messagebox.showerror("File Error", f"CSV file not found at '{csv_filename}'")
            self.status_var.set("Error: CSV file not found.")
            return
        except Exception as e:
            messagebox.showerror("CSV Error", f"An unexpected error occurred while reading the CSV: {e}")
            self.status_var.set("Error: Failed to read CSV.")
            return

        # --- Update GUI after processing ---
        self.status_var.set("Populating results...")

        # Display any warnings encountered during CSV read
        if temp_warnings:
             self._log_to_details("--- CSV Read Warnings ---")
             for warning in temp_warnings:
                 self._log_to_details(warning)
             self._log_to_details("-" * 25 + "\n")


        if not self.analysis_results:
            self._log_to_details("No valid bond data found in the CSV file to analyze.")
            self.status_var.set("Analysis complete: No valid data found.")
            return

        # Populate dropdown
        self.bond_selector['values'] = self.bond_confirmations
        if self.bond_confirmations:
            self.bond_selector.current(0) # Select the first bond
            self.on_bond_select() # Trigger display for the first bond

        # Calculate and display summary
        recommended_count = 0
        total_net_gain = 0.0
        for data in self.analysis_results.values():
            metrics = data['metrics']
            # Only count if no error and net gain is positive
            if not metrics.get('error') and metrics.get('net_gain_or_loss', 0) > 0:
                recommended_count += 1
                total_net_gain += metrics.get('net_gain_or_loss', 0)

        self.summary_count_var.set(f"{recommended_count} bond(s)")
        self.summary_gain_var.set(f"${total_net_gain:,.2f}")

        self.status_var.set(f"Analysis complete. Processed {len(self.analysis_results)} bonds.")

        # Add disclaimers to the detail view initially or after warnings
        self._log_to_details("\n" + "=" * 50)
        self._log_to_details("--- Important Disclaimers ---")
        self._log_to_details("* Select a bond from the dropdown above to see its specific analysis.")
        self._log_to_details("* This is an estimation based on the inputs and assumptions provided.")
        self._log_to_details("* Penalty calculation is an estimate based on the CURRENT composite rate")
        self._log_to_details("  and CURRENT value provided in the CSV (verify on TreasuryDirect).")
        self._log_to_details("* Assumes the reinvested amount ('Net Proceeds') matches the new bond purchase.")
        self._log_to_details("* Does NOT account for state/local taxes (I Bond interest is typically exempt).")
        self._log_to_details("* Does NOT factor in the annual $10,000 purchase limit per SSN.")
        self._log_to_details("* Does NOT compare returns against other potential investments.")
        self._log_to_details("* Market conditions and future inflation rates can change.")
        self._log_to_details("* Consult with a qualified financial advisor before making decisions.")
        self._log_to_details("-" * 50)


# --- Run the GUI Application ---
if __name__ == "__main__":
    root = tk.Tk()
    # Optional: Add theme for a more modern look if available
    try:
        style = ttk.Style(root)
        # Choose theme based on OS or preference ('clam', 'alt', 'default', 'classic', 'vista', 'xpnative')
        if sys.platform == "win32":
            style.theme_use('vista')
        else:
            style.theme_use('clam') # A common cross-platform theme
    except tk.TclError:
        print("ttk themes not available, using default.") # Fallback

    app = IBondAnalyzerApp(root)
    root.mainloop()
