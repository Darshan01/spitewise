"""
routes/summary.py
Debt summary:
  GET /groups/<id>/summary?simplify=true|false
  Returns JSON with per-person debt/credit breakdown.
  Calls debt_calculator.calculate() with the group's current transactions.
"""

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from bson import ObjectId

from db import get_db, oid
from debt_calculator import calculate

summary_bp = Blueprint("summary", __name__)


@summary_bp.route("/groups/<group_id>/summary")
@login_required
def summary(group_id):
    db = get_db()

    group = db.groups.find_one({"_id": oid(group_id)})
    if not group:
        abort(404)
    if ObjectId(current_user.id) not in group.get("member_ids", []):
        abort(403)

    # Resolve member emails and names in insertion order
    member_docs = list(db.users.find({"_id": {"$in": group.get("member_ids", [])}}))
    id_to_doc = {str(m["_id"]): m for m in member_docs}

    # Build list of member emails (preserving order)
    members = [
        id_to_doc[str(mid)]["email"]
        for mid in group["member_ids"]
        if str(mid) in id_to_doc
    ]

    # Build email-to-name mapping for display
    email_to_name = {
        id_to_doc[str(mid)]["email"]: id_to_doc[str(mid)].get("name", id_to_doc[str(mid)]["email"])
        for mid in group["member_ids"]
        if str(mid) in id_to_doc
    }

    # Load transactions with emails
    txns_raw = list(db.transactions.find({"group_id": group["_id"]}))
    transactions = [
        {
            "paid_by": t["paid_by"],
            "amount": t["amount"],
            "split_among": t.get("split_among", []),
        }
        for t in txns_raw
    ]

    # Read simplify param (defaults to true)
    simplify_param = request.args.get("simplify", "true").lower()
    simplify = simplify_param != "false"

    try:
        result = calculate(members, transactions, email_to_name=email_to_name, simplify=simplify)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    result["group"] = {"id": group_id, "name": group["name"]}
    result["simplify"] = simplify
    return jsonify(result)