from flask import Blueprint, render_template
from catalog.db import get_db, db_read_schema, db_read_columns, db_read_informations

bp = Blueprint("catalog", __name__)


@bp.route("/")
def home():
    db = get_db()
    schemas = db_read_schema(db)
    return render_template("home.html", schemas=schemas)


@bp.route("/<string:schema>/<string:table>")
def table(schema: str, table: str):
    db = get_db()
    columns = db_read_columns(db, schema, table)
    table_informations = db_read_informations(db, schema, table)
    return render_template(
        "table.html",
        schema=schema,
        table=table,
        columns=columns,
        table_informations=table_informations,
    )
