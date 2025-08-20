# spitewise
Program to organize group payments and simplify debts.

Command usage: python spitewise.py <inputFilePath> <OptionalSimplifyDebtsBool>

Input file format:
- First line: comma-separated list of names (e.g. "Alice, Bob, Charlie")
- Second line: empty
- Subsequent lines: transactions in the format "PaidBy - Description - Amount - (Optional: SplitAmong)"
  - PaidBy: name of the person who paid (must match a name from the first line)
  - Description: brief description of the transaction (not used in calculations)
  - Amount: total amount paid (float)
  - SplitAmong: optional comma-separated list of names who are splitting the cost (if omitted, split among all equally)
