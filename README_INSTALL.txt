==========================================
  Payment Management System v3 - Windows
==========================================

NEW IN v3:
  - Calendar date picker on all date fields (DD-MM-YYYY)
  - Vendor Opening Balance (carry-forward from last FY)
  - Edit vouchers, purchases, credit/debit notes from Day Book / Ledger
  - FY Carry-Forward: closing balances auto become opening balances
  - Ledger shows payable breakdown (Opening + Purchases + DN - Payments - CN)
  - Opening Balance row in Ledger for full running balance
  - Vendor refresh button on Purchase Voucher screen

REQUIREMENTS:
  - Windows 10 / 11 (64-bit)
  - Python 3.10 or newer  (https://python.org/downloads)
    (tick "Add Python to PATH" during installation)
  - Internet connection for first-time setup only

==========================================
  STEP 1 - INSTALL PYTHON DEPENDENCIES
==========================================

1. Open a Command Prompt (cmd) in this folder.
   (Hold Shift, right-click inside the folder -> "Open PowerShell/CMD here")

2. Run:
       pip install -r requirements.txt

==========================================
  STEP 2 - RUN THE APP (without packaging)
==========================================

   python main.py

That's it! The app will open and ask you to create your first entity.

==========================================
  STEP 3 - BUILD A STANDALONE .EXE
==========================================

Double-click:  build.bat

Wait for it to finish (~2-5 minutes).
The .exe will be created at:  dist\PaymentManagementSystem.exe

You can copy this single .exe to any Windows PC and run it directly.
No Python installation needed on the target machine.

==========================================
  STEP 4 - CREATE AN INSTALLER (Optional)
==========================================

1. Download and install Inno Setup:
   https://jrsoftware.org/isinfo.php

2. Open Inno Setup Compiler.
3. Open the file: setup.iss
4. Click Build -> Compile.
5. The installer will be created in: installer_output\PMS_Setup.exe

Distribute PMS_Setup.exe to install the app on any Windows PC.

==========================================
  VENDOR CATEGORIES
==========================================

  expense   : Normal vendors, no invoice tracking
  creditor  : Invoice-based vendors with payable balance tracking
              (supports Opening Balance from previous year)

  Payable = Opening Balance + Purchases + Debit Notes
            - Payments - Credit Notes

==========================================
  FY CARRY-FORWARD
==========================================

From the Entity screen, click "New FY" next to any entity.
Check "Carry forward closing balances" to automatically:
  - Copy each creditor's net payable -> vendor opening_balance
  - Copy each account's closing balance -> account opening_balance

The new FY becomes active immediately.

==========================================
  FILE STRUCTURE
==========================================

  main.py                    Entry point
  database.py                SQLite database layer
  date_utils.py              Calendar date picker widget
  entity_screen.py           Entity selection + New FY screen
  main_window.py             Main app with sidebar navigation
  dashboard_frame.py         Dashboard (stats + chart)
  vendor_master_frame.py     Vendor management (with opening balance)
  accounts_master_frame.py   Account management
  voucher_entry_frame.py     Payment & transfer voucher entry
  purchase_voucher_frame.py  Purchase voucher entry
  credit_debit_note_frame.py Credit & Debit note entry
  daybook_frame.py           Day Book (all transactions, edit/cancel)
  ledger_frame.py            Vendor / Account ledger with payable card
  pdf_generator.py           PDF voucher printing (A5)
  requirements.txt           Python packages needed
  build.bat                  Builds the .exe
  setup.iss                  Inno Setup script for installer

==========================================
  DATA STORAGE
==========================================

Each entity stores all data in a separate SQLite database file (.db).
Choose your data folder on first launch. Back it up regularly.

Dates: displayed as DD-MM-YYYY, stored as YYYY-MM-DD internally.

==========================================
  SUPPORT
==========================================

If you encounter any issues:
1. Make sure Python is added to PATH.
2. Re-run: pip install -r requirements.txt
3. Run: python main.py and check the error in the terminal.
