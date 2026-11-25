"""HTTP layer of the expenses service: JSON in, JSON out. Each route reads
the request, calls service.py and returns the result. No SQL here."""
from flask import Blueprint, jsonify, request

import service
from db import get_db
from utils import ValidationError, parse_month

bp = Blueprint("expenses", __name__)


@bp.errorhandler(ValidationError)
def bad_input(err):
    return jsonify(error=str(err)), 400


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send the expense as a JSON object.")
    return data


@bp.get("/api/expenses")
def list_expenses():
    month = parse_month(request.args.get("month"))
    return jsonify(month=month, expenses=service.list_expenses(get_db(), month))


@bp.post("/api/expenses")
def add_expense():
    data = json_body()
    expense = service.add_expense(
        get_db(),
        data.get("amount"),
        data.get("category"),
        data.get("description"),
        data.get("spent_on"),
    )
    return jsonify(expense), 201


@bp.delete("/api/expenses/<int:expense_id>")
def delete_expense(expense_id):
    if not service.delete_expense(get_db(), expense_id):
        return jsonify(error="That expense doesn't exist (maybe it was already deleted)."), 404
    return "", 204


@bp.get("/api/expenses/totals")
def totals():
    """Called by the budgets service (ADR-6). Same path and response shape as in A1."""
    month = parse_month(request.args.get("month"))
    return jsonify(month=month, totals=service.totals_by_category(get_db(), month))


@bp.get("/api/expenses/categories")
def categories():
    return jsonify(categories=service.known_categories(get_db()))
