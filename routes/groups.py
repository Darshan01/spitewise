"""
routes/groups.py
Group management routes:
  GET    /                       — redirect to /groups
  GET    /groups                 — list user's groups (dashboard)
  POST   /groups                 — create a new group
  GET    /groups/<id>            — group detail page
  POST   /groups/<id>/members    — add a member by email
  DELETE /groups/<id>            — delete group (creator only)
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, abort, flash
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timezone

from db import get_db, oid
from models import User

groups_bp = Blueprint("groups", __name__)


def _group_or_404(group_id, db=None):
    if db is None:
        db = get_db()
    group = db.groups.find_one({"_id": oid(group_id)})
    if not group:
        abort(404)
    return group


def _require_member(group):
    if ObjectId(current_user.id) not in group.get("member_ids", []):
        abort(403)


# ── Routes ──────────────────────────────────────────────────────────────────

@groups_bp.route("/")
@login_required
def root():
    return redirect(url_for("groups.index"))


@groups_bp.route("/groups")
@login_required
def index():
    db = get_db()
    raw = db.groups.find({"member_ids": ObjectId(current_user.id)}).sort("created_at", -1)

    groups = []
    for g in raw:
        members = list(db.users.find({"_id": {"$in": g.get("member_ids", [])}}))
        txn_count = db.transactions.count_documents({"group_id": g["_id"]})
        groups.append({
            "id": str(g["_id"]),
            "name": g["name"],
            "members": [{"name": m.get("name", m["email"]), "avatar": m.get("avatar", "")} for m in members],
            "txn_count": txn_count,
            "created_at": g.get("created_at"),
        })

    return render_template("groups.html", groups=groups)


@groups_bp.route("/groups", methods=["POST"])
@login_required
def create():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Group name is required."}), 400

    db = get_db()
    result = db.groups.insert_one({
        "name": name,
        "member_ids": [ObjectId(current_user.id)],
        "created_by": ObjectId(current_user.id),
        "created_at": datetime.now(timezone.utc),
    })
    group_id = str(result.inserted_id)

    if request.is_json:
        return jsonify({"id": group_id, "name": name}), 201
    return redirect(url_for("groups.detail", group_id=group_id))


@groups_bp.route("/groups/<group_id>")
@login_required
def detail(group_id):
    db = get_db()
    group = _group_or_404(group_id, db)
    _require_member(group)

    members = list(db.users.find({"_id": {"$in": group.get("member_ids", [])}}))
    member_names = [m.get("name", m["email"]) for m in members]

    txns_raw = list(db.transactions.find({"group_id": group["_id"]}).sort("created_at", -1))
    transactions = []
    for t in txns_raw:
        transactions.append({
            "id": str(t["_id"]),
            "paid_by": t["paid_by"],
            "name": t["name"],
            "description": t.get("description", ""),
            "amount": t["amount"],
            "split_among": t.get("split_among", []),
            "split_among_names": t.get("split_among_names", []),
            "confirmed_payers": t.get("confirmed_payers", []),
            "payer_confirmed": t.get("payer_confirmed", False),
            "recipient_confirmed": t.get("recipient_confirmed", False),
            "created_at": t.get("created_at"),
        })

    is_creator = str(group.get("created_by")) == current_user.id

    return render_template(
        "group_detail.html",
        group={"id": group_id, "name": group["name"]},
        members=member_names,
        transactions=transactions,
        is_creator=is_creator,
        current_user_email=current_user.email,
        member_docs=[{"name": m.get("name", m["email"]), "email": m["email"], "avatar": m.get("avatar", "")} for m in members],
    )


@groups_bp.route("/groups/<group_id>/members", methods=["POST"])
@login_required
def add_member(group_id):
    db = get_db()
    group = _group_or_404(group_id, db)
    _require_member(group)

    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required."}), 400

    user = User.get_by_email(email)
    if not user:
        return jsonify({"error": f"No account found for '{email}'. They need to sign in to Spitewise first."}), 404

    if ObjectId(user.id) in group.get("member_ids", []):
        return jsonify({"error": "That person is already in the group."}), 409

    db.groups.update_one(
        {"_id": group["_id"]},
        {"$addToSet": {"member_ids": ObjectId(user.id)}}
    )
    return jsonify({"message": f"{user.name} added.", "member": user.to_dict()}), 200


@groups_bp.route("/groups/<group_id>", methods=["DELETE"])
@login_required
def delete(group_id):
    db = get_db()
    group = _group_or_404(group_id, db)

    if str(group.get("created_by")) != current_user.id:
        return jsonify({"error": "Only the group creator can delete it."}), 403

    db.transactions.delete_many({"group_id": group["_id"]})
    db.groups.delete_one({"_id": group["_id"]})
    return jsonify({"message": "Group deleted."}), 200