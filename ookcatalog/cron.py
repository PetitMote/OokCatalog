from flask import Blueprint
from ookcatalog.db import (
    get_db,
    db_tables_updating,
)
from datetime import date, timedelta
from flask_babel import gettext as _

bp = Blueprint("cron", __name__)


@bp.cli.command("tables-updating")
def tables_updating():
    today = date.today()  # Getting today’s date
    tables_updating = {}  # Container for results
    db = get_db()
    tables_updating["this_month"] = db_tables_updating(
        db, today.month
    )  # Getting this month updates
    tables_updating_text = _("# This month updates:")  # Text result
    for table in tables_updating["this_month"]:
        # Putting table schema and name in the text result
        tables_updating_text += "\n{table}".format(
            table=f"{table['table_schema']}.{table['table_name']}"
        )

    if today.day <= 10:  # If in first part of the month
        last_month = (
            today.replace(day=1) - timedelta(days=1)
        ).month  # Getting previous month
        tables_updating["last_month"] = db_tables_updating(
            db, last_month
        )  # Getting previous updates
        text = _("# Last month updates:")  # Temporary text
        for table in tables_updating["last_month"]:
            text += "\n{table}".format(
                table=f"{table['table_schema']}.{table['table_name']}"
            )
        tables_updating_text = (
            text + "\n\n" + tables_updating_text
        )  # Putting temporary text in result text

    if today.day > 20:  # If in third part of the month
        next_month = (
            today.replace(day=25) + timedelta(days=10)
        ).month  # Getting next month
        tables_updating["next_month"] = db_tables_updating(
            db, next_month
        )  # Getting next month updates
        text = _("# Next month updates:")  # Temporary text
        for table in tables_updating["next_month"]:
            text += "\n{table}".format(
                table=f"{table['table_schema']}.{table['table_name']}"
            )
        tables_updating_text += "\n\n" + text  # Putting temporary text in result text

    print(tables_updating_text)  # Printing the result as this is a CLI command
