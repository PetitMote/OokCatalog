from flask import Blueprint, render_template, request
from ookcatalog.db import (
    get_db,
    db_read_schema,
    db_read_columns,
    db_read_informations,
    db_search,
)

bp = Blueprint("ookcatalog", __name__)


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


@bp.route("/search")
def search():
    db = get_db()
    query = request.args.get("q")
    search_results = db_search(db, query)
    return render_template(
        "search.html",
        search_results=search_results,
    )
