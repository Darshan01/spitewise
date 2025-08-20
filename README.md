# spitewise
Program to organize group payments and simplify debts.

Command usage: python spitewise.py <inputFilePath> <OptionalSimplifyDebtsBool>

Simplify debts is set to true by default. This option makes it so that you do not make unnecessary transactions. For example, if Alice owes Bob $15, and Bob owes Alice $10, instead of making two transactions, the program will just show that Alice owes Bob $5.

Input file format:
- First line: comma-separated list of names (e.g. "Alice, Bob, Charlie")
- Second line: empty
- Subsequent lines: transactions in the format "PaidBy - Description - Amount - (Optional: SplitAmong)"
  - PaidBy: name of the person who paid (must match a name from the first line)
  - Description: brief description of the transaction (not used in calculations)
  - Amount: total amount paid (float)
  - SplitAmong: optional comma-separated list of names who are splitting the cost (if omitted, split among all equally)

See the sample input and output files for examples.

Python version 3.13.1