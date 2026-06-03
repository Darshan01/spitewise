"""
routes/transactions.py
Transaction CRUD:
  GET    /groups/<id>/transactions   — list transactions (JSON)
  POST   /groups/<id>/transactions   — create transaction
  PUT    /transactions/<txn_id>      — edit transaction
  DELETE /transactions/<txn_id>      — delete transaction
"""

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timezone

from db import get_db, oid

transactions_bp = Blueprint("transactions", __name__)


def _group_member_or_403(group_id, db):
    group = db.groups.find_one({"_id": oid(group_id)})
    if not group:
        abort(404)
    if ObjectId(current_user.id) not in group.get("member_ids", []):
        abort(403)
    return group


def _txn_or_404(txn_id, db):
    txn = db.transactions.find_one({"_id": oid(txn_id)})
    if not txn:
        abort(404)
    return txn


def _serialize(txn):
    return {
        "id": str(txn["_id"]),
        "paid_by": txn["paid_by"],
        "name": txn["name"],
        "description": txn.get("description", ""),
        "amount": txn["amount"],
        "split_among": txn.get("split_among", []),
        "split_among_names": txn.get("split_among_names", []),
        "confirmed_payers": txn.get("confirmed_payers", []),
        "payer_confirmed": txn.get("payer_confirmed", False),
        "recipient_confirmed": txn.get("recipient_confirmed", False),
        "created_at": txn.get("created_at", "").isoformat() if txn.get("created_at") else "",
    }


# ── Routes ──────────────────────────────────────────────────────────────────

@transactions_bp.route("/groups/<group_id>/transactions", methods=["GET"])
@login_required
def list_transactions(group_id):
    db = get_db()
    _group_member_or_403(group_id, db)
    txns = list(db.transactions.find({"group_id": oid(group_id)}).sort("created_at", -1))
    return jsonify([_serialize(t) for t in txns])


@transactions_bp.route("/groups/<group_id>/transactions", methods=["POST"])
@login_required
def create_transaction(group_id):
    db = get_db()
    group = _group_member_or_403(group_id, db)

    data = request.get_json(silent=True) or request.form.to_dict()
    paid_by = (data.get("paid_by") or "").strip()
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    amount_raw = data.get("amount")
    split_among_raw = data.get("split_among", [])
    split_among_names_raw = data.get("split_among_names", [])

    # Normalise split_among: may arrive as comma-separated string or list
    if isinstance(split_among_raw, str):
        split_among = [s.strip() for s in split_among_raw.split(",") if s.strip()]
    else:
        split_among = [s.strip() for s in split_among_raw if s.strip()]
        
    if isinstance(split_among_names_raw, str):
        split_among_names = [s.strip() for s in split_among_names_raw.split(",") if s.strip()]
    else:
        split_among_names = [s.strip() for s in split_among_names_raw if s.strip()]

    if not paid_by:
        return jsonify({"error": "paid_by is required."}), 400
    if not description:
        return jsonify({"error": "description is required."}), 400

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a positive number."}), 400

    # Validate paid_by and split_among against group members
    members = list(db.users.find({"_id": {"$in": group.get("member_ids", [])}}))
    member_emails = {m["email"] for m in members}

    if paid_by not in member_emails:
        return jsonify({"error": f"'{paid_by}' is not a member of this group."}), 400

    for email in split_among:
        if email not in member_emails:
            return jsonify({"error": f"'{email}' is not a member of this group."}), 400

    result = db.transactions.insert_one({
        "group_id": oid(group_id),
        "paid_by": paid_by,
        "name": name,
        "description": description,
        "amount": amount,
        "split_among": split_among,
        "split_among_names": split_among_names,
        "created_by": ObjectId(current_user.id),
        "created_at": datetime.now(timezone.utc),
    })

    new_txn = db.transactions.find_one({"_id": result.inserted_id})
    return jsonify(_serialize(new_txn)), 201

@transactions_bp.route("/groups/<group_id>/transactions", methods=["DELETE"])
@login_required
def delete_all_transactions(group_id):
    db = get_db()
    _group_member_or_403(group_id, db)
    db.transactions.delete_many({"group_id": oid(group_id)})
    return jsonify({"message": "All transactions deleted."}), 200

@transactions_bp.route("/transactions/<txn_id>", methods=["PUT"])
@login_required
def update_transaction(txn_id):
    db = get_db()
    txn = _txn_or_404(txn_id, db)

    # Confirm caller is a member of the transaction's group
    group = db.groups.find_one({"_id": txn["group_id"]})
    if not group or ObjectId(current_user.id) not in group.get("member_ids", []):
        abort(403)

    data = request.get_json(silent=True) or {}
    updates = {}

    # Get member emails for validation
    members = list(db.users.find({"_id": {"$in": group.get("member_ids", [])}}))
    member_emails = {m["email"] for m in members}

    if "paid_by" in data:
        paid_by = data["paid_by"].strip()
        if paid_by not in member_emails:
            return jsonify({"error": f"'{paid_by}' is not a member of this group."}), 400
        updates["paid_by"] = paid_by
    
    if "name" in data:
        updates["name"] = data["name"].strip()

    if "description" in data:
        updates["description"] = data["description"].strip()

    if "amount" in data:
        try:
            amt = float(data["amount"])
            if amt <= 0:
                raise ValueError
            updates["amount"] = amt
        except (TypeError, ValueError):
            return jsonify({"error": "amount must be a positive number."}), 400

    if "split_among" in data:
        raw = data["split_among"]
        if isinstance(raw, str):
            split_among = [s.strip() for s in raw.split(",") if s.strip()]
        else:
            split_among = [s.strip() for s in raw if s.strip()]

        for email in split_among:
            if email not in member_emails:
                return jsonify({"error": f"'{email}' is not a member of this group."}), 400

        updates["split_among"] = split_among
    
    if "split_among_names" in data:
        raw = data["split_among_names"]
        if isinstance(raw, str):
            split_among_names = [s.strip() for s in raw.split(",") if s.strip()]
        else:
            split_among_names = [s.strip() for s in raw if s.strip()]
        updates["split_among_names"] = split_among_names

    if not updates:
        return jsonify({"error": "No valid fields to update."}), 400

    db.transactions.update_one({"_id": txn["_id"]}, {"$set": updates})
    updated = db.transactions.find_one({"_id": txn["_id"]})
    return jsonify(_serialize(updated))


@transactions_bp.route("/transactions/<txn_id>", methods=["DELETE"])
@login_required
def delete_transaction(txn_id):
    db = get_db()
    txn = _txn_or_404(txn_id, db)

    group = db.groups.find_one({"_id": txn["group_id"]})
    if not group or ObjectId(current_user.id) not in group.get("member_ids", []):
        abort(403)

    db.transactions.delete_one({"_id": txn["_id"]})
    return jsonify({"message": "Transaction deleted."}), 200


@transactions_bp.route("/transactions/<txn_id>/verify", methods=["POST"])
@login_required
def verify_payment(txn_id):
    """
    Two-step verification:
      - action "confirm_payment": a debtor confirms they have paid their share.
        Anyone who owes money on this transaction can do this.
        Tracked in `confirmed_payers` (list of emails who have confirmed).
        Once all debtors have confirmed, `payer_confirmed` is set True automatically.
      - action "approve_payment": the person who originally paid confirms they
        received the money from everyone. Sets `recipient_confirmed` = True.
        Only available once all debtors have confirmed.
    A transaction is fully verified when both flags are True.
    """
    db = get_db()
    txn = _txn_or_404(txn_id, db)

    group = db.groups.find_one({"_id": txn["group_id"]})
    if not group or ObjectId(current_user.id) not in group.get("member_ids", []):
        abort(403)

    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if action == "confirm_payment":
        # Any debtor can confirm they paid their share.
        # The payer of the transaction cannot confirm their own payment.
        if current_user.email == txn["paid_by"]:
            return jsonify({"error": "You paid for this transaction — use 'approve_payment' once everyone has confirmed."}), 403

        confirmed = txn.get("confirmed_payers", [])
        if current_user.email in confirmed:
            return jsonify({"error": "You have already confirmed this payment."}), 409

        confirmed.append(current_user.email)

        # Work out who actually owes money on this transaction
        split_among = txn.get("split_among", [])
        members_raw = list(db.users.find({"_id": {"$in": group.get("member_ids", [])}}))
        all_member_emails = [m["email"] for m in members_raw]

        # Debtors = split_among (if specified) else everyone except the payer
        if split_among:
            debtors = [e for e in split_among if e != txn["paid_by"]]
        else:
            debtors = [e for e in all_member_emails if e != txn["paid_by"]]

        all_confirmed = all(d in confirmed for d in debtors)

        db.transactions.update_one(
            {"_id": txn["_id"]},
            {"$set": {
                "confirmed_payers": confirmed,
                "payer_confirmed": all_confirmed,
            }}
        )
        updated = db.transactions.find_one({"_id": txn["_id"]})
        return jsonify({
            "message": "Payment confirmed." + (" All debtors have confirmed — the payer can now approve." if all_confirmed else ""),
            "transaction": _serialize(updated),
            "all_debtors_confirmed": all_confirmed,
        }), 200

    elif action == "approve_payment":
        # Only the original payer can approve receipt of money.
        if current_user.email != txn["paid_by"]:
            return jsonify({"error": "Only the person who paid can approve receipt of money."}), 403

        if not txn.get("payer_confirmed"):
            return jsonify({"error": "Not all debtors have confirmed their payments yet."}), 400

        if txn.get("recipient_confirmed"):
            return jsonify({"error": "This transaction is already fully verified."}), 409

        db.transactions.update_one(
            {"_id": txn["_id"]},
            {"$set": {"recipient_confirmed": True}}
        )
        updated = db.transactions.find_one({"_id": txn["_id"]})
        return jsonify({
            "message": "Payment approved. This transaction is now fully verified and removed from debt calculations.",
            "transaction": _serialize(updated),
        }), 200

    else:
        return jsonify({"error": "Invalid action. Use 'confirm_payment' or 'approve_payment'."}), 400