"""
Use this file to organize group payments and simplify debts

Command usage: python spitewise.py <inputFilePath> <OptionalSimplifyDebtsBool>

Input file format:
- First line: comma-separated list of names (e.g. "Alice, Bob, Charlie")
- Second line: empty
- Subsequent lines: transactions in the format "PaidBy - Description - Amount - (Optional: SplitAmong)"
  - PaidBy: name of the person who paid (must match a name from the first line)
  - Description: brief description of the transaction (not used in calculations)
  - Amount: total amount paid (float)
  - SplitAmong: optional comma-separated list of names who are splitting the cost (if omitted, split among all equally)
"""

import sys

#make sure input file path is provided
if len(sys.argv) < 2:
    print("Error: please provide the input file path as the first argument, or 'help' for usage information.")
    exit(1)

#help message
if sys.argv[1].lower() == "help" or sys.argv[1].lower() == "h":
    print()
    print("Usage: python spitewise.py <inputFilePath> <OptionalSimplifyDebtsBool>")
    print("Example: python spitewise.py lakeGeorgeSplit.txt True")
    print("If the second argument is not provided, it defaults to True.")
    print()
    exit(0)


#make sure input file is a .txt file
inPath = sys.argv[1]
if inPath.lower().endswith('.txt') is False:
    print("Error: The input file must be a .txt file.")
    exit(1)

#simplify debts is true by default, can be changed optionally
simplify = True 
if len(sys.argv) > 2:
    simplify = bool(sys.argv[2].lower() == 'true')

#make sure input file exists
try:
    file = open(inPath, 'r')
except FileNotFoundError:
    print(f"Error: The file '{inPath}' does not exist.")
    exit(1)

#read the names on the first line and use dict for quick access
namesLine = [name.strip() for name in file.readline().strip().split(",")]
people = dict([(namesLine[i].lower(), i) for i in range(len(namesLine))])

#create 2d payment matrix
paymentMatrix = [[0 for i in range(len(namesLine))] for j in range(len(namesLine))]

file.readline() #skip empty line

lineNum = 3
for transaction in file:
    transaction = transaction.strip().split(" - ")

    if len(transaction) < 3:
        print(f"Error: in line {lineNum} in the input, there are not enough fields. Expected at least 3 fields (payer, description, and amount).")
        file.close()
        exit(1)
    
    paidBy = transaction[0].lower()
    try:
        paidByIndex = people[paidBy]
    except KeyError:
        print(f"Error: in line {lineNum} in the input, '{paidBy}' is not listed in the names on the first line.")
        file.close()
        exit(1)
    
    #store the transaction amount
    try:
        amount = float(transaction[2])
    except ValueError:
        print(f"Error: in line {lineNum} in the input, '{transaction[2]}' is not a valid number.")
        file.close()
        exit(1)
    
    #if the transaction is split among certain people, store their indices
    splitAmong = []
    if len(transaction) == 4:
        for name in transaction[3].strip().split(","):
            name = name.strip().lower()
            try:
                splitAmong.append(people[name])
            except KeyError:
                print(f"Error: in line {lineNum} in the input, '{name}' is not listed in the names on the first line.")
                file.close()
                exit(1)
            

    #simulate the payments in the payment matrix
    for splitterIndex in range(len(namesLine)):
        
        #record the total amount paid by each person in the diagonal
        if splitterIndex == paidByIndex:
            paymentMatrix[splitterIndex][paidByIndex] += amount
            continue
        
        #if there is nobody specified, split among everyone equally
        if len(splitAmong) == 0:
            paymentMatrix[splitterIndex][paidByIndex] += amount / len(namesLine)
            if simplify: paymentMatrix[paidByIndex][splitterIndex] -= amount / len(namesLine)
        
        #otherwise, split among the specified people
        else:
            if splitterIndex in splitAmong:
                paymentMatrix[splitterIndex][paidByIndex] += amount / len(splitAmong)
                if simplify: paymentMatrix[paidByIndex][splitterIndex] -= amount / len(splitAmong)
        
    lineNum += 1

if simplify:
    #iterate through each person's list of debts
    for i in range(len(namesLine)):
        
        #iterate through each person they owe money to
        for j in range(len(namesLine)):
            
            if i == j: continue #skip self
            
            #if person i doesn't owe person j money, skip
            # if paymentMatrix[i][j] <= 0: continue
            
            for k in range(len(namesLine)):
                
                if i == k or j == k: continue
                
                #if person i doesn't owe person k money, skip
                if paymentMatrix[i][k] <= 0: continue
                
                #if person k doesn't own person j money, skip
                if paymentMatrix[k][j] <= 0: continue
                
                #if person k owes person j more than or equal to what person i owes person k, settle the debt
                if paymentMatrix[k][j] >= paymentMatrix[i][k]:
                    
                    #person i pays person j the amount they owe person k
                    paymentMatrix[i][j] += paymentMatrix[i][k] 
                    paymentMatrix[j][i] -= paymentMatrix[i][k]
                    
                    #person k no longer owes person j that money
                    paymentMatrix[k][j] -= paymentMatrix[i][k]
                    paymentMatrix[j][k] += paymentMatrix[i][k]
                    
                    #person i no longer owes person k money
                    paymentMatrix[i][k] = 0
                    paymentMatrix[k][i] = 0

for nameIndex in range(len(namesLine)):
    owed = sum(paymentMatrix[nameIndex]) - paymentMatrix[nameIndex][nameIndex]
    
    #if they are owed money, show how much and their total expenditure
    if owed <= 0:
        print(f"{namesLine[nameIndex]} is owed ${-1*owed:.2f} in total")
        print(f"\t{namesLine[nameIndex]} has paid ${(paymentMatrix[nameIndex][nameIndex]):.2f} in total")
        if simplify: print(f"\t{namesLine[nameIndex]} will have spent ${(paymentMatrix[nameIndex][nameIndex] + owed):.2f} after debts are settled")
    
    #if they owe money, show how much, to whom, and their total expenditure
    if owed > 0:
        print(f"{namesLine[nameIndex]} owes:")
        totalDebt = 0
        for debt in range(len(namesLine)):
            if paymentMatrix[nameIndex][debt] > 0 and debt != nameIndex:
                print(f"\t{namesLine[nameIndex]} owes {namesLine[debt]} ${paymentMatrix[nameIndex][debt]:.2f}")
                totalDebt += paymentMatrix[nameIndex][debt]
        print(f"\tFor a total of: ${totalDebt:.2f}")
        print()
        print(f"\t{namesLine[nameIndex]} spent ${(paymentMatrix[nameIndex][nameIndex]):.2f} in total before any debts are settled")
        if simplify: print(f"\t{namesLine[nameIndex]} will have spent ${(paymentMatrix[nameIndex][nameIndex] + owed):.2f} after debts are settled")
    print()

file.close()