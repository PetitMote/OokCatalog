import click
from ookcatalog import create_app
from flask.cli import FlaskGroup
from ookcatalog.db import (
    get_db,
    db_tables_updating,
    db_catalog_retrieve_tables,
    db_tables_missing_comment,
    db_tables_with_columns_missing_comment,
    db_tables_missing_ookcatalog_details,
)
from datetime import date, timedelta
from flask_babel import gettext as _

@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("tables-updating")
def tables_updating():
    """List tables updating this month and last or next month."""
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


@cli.command("update-tables-catalog")
def update_tables_catalog():
    """Insert existing tables in public.ookcatalog so you can set their information."""
    db = get_db()
    tables_inserted = db_catalog_retrieve_tables(db)
    print(_("# Tables inserted in public.ookcatalog:"))
    for table in tables_inserted:
        print(f"{table['table_schema']}.{table['table_name']}")


@cli.command("tables-missing-comments")
def get_tables_missing_comments():
    """List tables missing a comment on them or on one of their columns."""
    db = get_db()
    print(_("# Tables missing comments:"))
    for table in db_tables_missing_comment(db):
        print(f"{table['table_schema']}.{table['table_name']}")
    print(_("\n# Tables with column missing comments:"))
    for table in db_tables_with_columns_missing_comment(db):
        print(f"{table['table_schema']}.{table['table_name']}")
    print(_("\n# Tables missing OokCatalog details:"))
    for table in db_tables_missing_ookcatalog_details(db):
        print(f"{table['table_schema']}.{table['table_name']}")
