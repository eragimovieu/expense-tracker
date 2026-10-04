"""HTTP layer for the expenses domain. Each route reads the request, calls
expenses/service.py, and either renders a page or returns JSON. No SQL here."""
from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from db import get_db
from expenses import service
from utils import ValidationError, parse_month

bp = Blueprint("expenses", __name__)


@bp.get("/expenses")
def expenses_page():
    try:
        month = parse_month(request.args.get("month"))
    except ValidationError as err:
        flash(str(err), "error")
        return redirect(url_for("expenses.expenses_page"))

    conn = get_db()
    totals = service.totals_by_category(conn, month)
    return render_template(
        "expenses.html",
        month=month,
        expenses=service.list_expenses(conn, month),
        totals=totals,
        month_total=sum(totals.values()),
        categories=service.known_categories(conn),
        today=date.today().isoformat(),
    )


@bp.post("/expenses")
def add_expense():
    form = request.form
    try:
        service.add_expense(
            get_db(),
            form.get("amount"),
            form.get("category"),
            form.get("description"),
            form.get("spent_on"),
        )
        flash("Expense added.", "success")
    except ValidationError as err:
        flash(str(err), "error")
    # Post/Redirect/Get: after a form POST, redirect so a page refresh
    # doesn't submit the same expense twice.
    return redirect(url_for("expenses.expenses_page", month=form.get("month")))


@bp.post("/expenses/<int:expense_id>/delete")
def delete_expense(expense_id):
    if service.delete_expense(get_db(), expense_id):
        flash("Expense deleted.", "success")
    else:
        flash("That expense was already deleted.", "error")
    return redirect(url_for("expenses.expenses_page", month=request.form.get("month")))


# --- JSON API -------------------------------------------------------------
# /api/expenses/totals is what a separate budgets service would call after
# the split (ADR-2).

@bp.get("/api/expenses")
def api_list_expenses():
    try:
        month = parse_month(request.args.get("month"))
    except ValidationError as err:
        return jsonify(error=str(err)), 400
    return jsonify(month=month, expenses=service.list_expenses(get_db(), month))


@bp.get("/api/expenses/totals")
def api_totals():
    try:
        month = parse_month(request.args.get("month"))
    except ValidationError as err:
        return jsonify(error=str(err)), 400
    return jsonify(month=month, totals=service.totals_by_category(get_db(), month))
