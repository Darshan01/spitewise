"""
debt_calculator.py
Pure calculation logic extracted from spitewise.py.
No file I/O, no sys.argv — just functions that take data and return results.
"""

def _sum_sign(values, positive=True, exclude_index=None):
    """Sum only positive or negative values in a list, optionally skipping one index."""
    total = 0
    for i, v in enumerate(values):
        if exclude_index is not None and i == exclude_index:
            continue
        if positive and v > 0:
            total += v
        elif not positive and v < 0:
            total += v
    return total


def calculate(members, transactions, email_to_name=None, simplify=True):
    """
    Calculate debts for a group.

    Args:
        members: list of email strings (unique identifiers), e.g. ["alice@example.com", "bob@example.com"]
        transactions: list of dicts, each with keys:
            - paid_by: str (email, must match a member)
            - amount: float
            - split_among: list[str] (emails; empty list means split among all)
        email_to_name: optional dict mapping email to display name, e.g. {"alice@example.com": "Alice"}
        simplify: bool — whether to reduce the number of transactions

    Returns:
        dict with key "people", a list of per-person summary dicts:
            {
                "email": str,
                "name": str,
                "spent": float,
                "owes": float,
                "owed": float,
                "net": float,
                "debts": [{"to": str, "to_name": str, "amount": float}, ...],
                "credits": [{"from": str, "from_name": str, "amount": float}, ...],
            }
    """
    if email_to_name is None:
        email_to_name = {}

    email_to_idx = {e: i for i, e in enumerate(members)}
    n = len(members)

    # Build payment matrix: matrix[i][j] means "person i owes person j this amount"
    # Diagonal: total spent by person i
    matrix = [[0.0] * n for _ in range(n)]

    for txn in transactions:
        payer = txn["paid_by"].strip()
        if payer not in email_to_idx:
            raise ValueError(f"Payer '{payer}' is not a member of this group.")
        payer_idx = email_to_idx[payer]

        try:
            amount = float(txn["amount"])
        except (TypeError, ValueError):
            raise ValueError(f"Invalid amount '{txn['amount']}' in transaction.")

        split_among_emails = [s.strip() for s in txn.get("split_among", [])]
        split_among_idxs = []
        for email in split_among_emails:
            if email not in email_to_idx:
                raise ValueError(f"Split member '{email}' is not a member of this group.")
            split_among_idxs.append(email_to_idx[email])

        for i in range(n):
            if i == payer_idx:
                matrix[i][payer_idx] += amount
                continue
            if not split_among_idxs:
                # Split equally among everyone
                matrix[i][payer_idx] += amount / n
                if simplify:
                    matrix[payer_idx][i] -= amount / n
            else:
                if i in split_among_idxs:
                    share = amount / len(split_among_idxs)
                    matrix[i][payer_idx] += share
                    if simplify:
                        matrix[payer_idx][i] -= share

    if simplify:
        _simplify_matrix(matrix, n)

    # Build output
    result = []
    for i, email in enumerate(members):
        owed = -1 * _sum_sign(matrix[i], positive=False, exclude_index=i)
        owes = _sum_sign(matrix[i], positive=True, exclude_index=i)

        debts = []
        for j in range(n):
            if j != i and matrix[i][j] > 0.005:
                to_email = members[j]
                debts.append({
                    "to": to_email,
                    "to_name": email_to_name.get(to_email, to_email),
                    "amount": round(matrix[i][j], 2)
                })

        credits = []
        for j in range(n):
            if j != i and matrix[i][j] < -0.005:
                from_email = members[j]
                credits.append({
                    "from": from_email,
                    "from_name": email_to_name.get(from_email, from_email),
                    "amount": round(-matrix[i][j], 2)
                })

        result.append({
            "email": email,
            "name": email_to_name.get(email, email),
            "spent": round(matrix[i][i], 2),
            "owes": round(owes, 2),
            "owed": round(owed, 2),
            "net": round(matrix[i][i] - owed + owes, 2),
            "debts": debts,
            "credits": credits,
        })

    return {"people": result}


def _simplify_matrix(matrix, n):
    """
    Reduce the number of transactions needed by collapsing chains:
    if A owes B and B owes C, A pays C directly.
    Modifies matrix in-place.
    """
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if matrix[i][j] <= 0:
                continue
            for k in range(n):
                if i == k or j == k:
                    continue
                if matrix[i][k] <= 0:
                    continue
                if matrix[k][j] <= 0:
                    continue
                if matrix[k][j] >= matrix[i][k]:
                    matrix[i][j] += matrix[i][k]
                    matrix[j][i] -= matrix[i][k]
                    matrix[k][j] -= matrix[i][k]
                    matrix[j][k] += matrix[i][k]
                    matrix[i][k] = 0.0
                    matrix[k][i] = 0.0