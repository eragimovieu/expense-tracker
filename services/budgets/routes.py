"""HTTP layer of the budgets service: JSON in, JSON out. No SQL here."""
from flask import Blueprint, current_app, jsonify, request

import expenses_client
import service
from db import get_db
from utils import ValidationError, parse_month

bp = Blueprint("budgets", __name__)


@bp.errorhandler(ValidationError)
def bad_input(err):
    return jsonify(error=str(err)), 400


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send the budget as a JSON object.")
    return data


@bp.get("/api/budgets/status")
def status():
    """The flow that crosses the seam: budgets are ours, spending comes from
    the expenses service. If expenses doesn't answer, the limits are still
    returned with spending_available: false (ADR-6)."""
    month = parse_month(request.args.get("month"))
    config = current_app.config
    try:
        totals = expenses_client.fetch_totals(
            config["EXPENSES_URL"], month, config["EXPENSES_TIMEOUT_S"]
        )
    except expenses_client.ExpensesUnavailable:
        totals = None
    return jsonify(service.status_report(get_db(), month, totals))


@bp.post("/api/budgets")
def save_budget():
    data = json_body()
    budget = service.set_budget(get_db(), data.get("category"), data.get("monthly_limit"))
    return jsonify(budget), 200


@bp.delete("/api/budgets/<int:budget_id>")
def delete_budget(budget_id):
    if not service.delete_budget(get_db(), budget_id):
        return jsonify(error="That budget doesn't exist (maybe it was already removed)."), 404
    return "", 204
