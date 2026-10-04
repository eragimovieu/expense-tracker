"""HTTP layer for the budgets domain. Reads the request, calls
budgets/service.py, renders a page or returns JSON. No SQL here."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from budgets import service
from db import get_db
from utils import ValidationError, parse_month

bp = Blueprint("budgets", __name__)


@bp.get("/budgets")
def budgets_page():
    try:
        month = parse_month(request.args.get("month"))
    except ValidationError as err:
        flash(str(err), "error")
        return redirect(url_for("budgets.budgets_page"))

    return render_template(
        "budgets.html",
        month=month,
        rows=service.budget_status(get_db(), month),
    )


@bp.post("/budgets")
def save_budget():
    try:
        category = service.set_budget(
            get_db(), request.form.get("category"), request.form.get("monthly_limit")
        )
        flash(f"Budget for '{category}' saved.", "success")
    except ValidationError as err:
        flash(str(err), "error")
    return redirect(url_for("budgets.budgets_page", month=request.form.get("month")))


@bp.post("/budgets/<int:budget_id>/delete")
def delete_budget(budget_id):
    if service.delete_budget(get_db(), budget_id):
        flash("Budget removed.", "success")
    else:
        flash("That budget was already removed.", "error")
    return redirect(url_for("budgets.budgets_page", month=request.form.get("month")))


@bp.get("/api/budgets/status")
def api_status():
    try:
        month = parse_month(request.args.get("month"))
    except ValidationError as err:
        return jsonify(error=str(err)), 400
    return jsonify(month=month, budgets=service.budget_status(get_db(), month))
