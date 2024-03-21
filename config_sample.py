SECRET_KEY = "<KEY>"  # As for now, OokCatalog does not make use of any cookie
DATABASE = {
    "HOST": "localhost",
    "PORT": "5432",
    "DBNAME": "ookcatalog",
    "USER": "ookcatalog",
    "PASSWORD": "password",
}
DATABASE_TITLE = "BDU"
# Language passed to PostgreSQL for full text search. Needed so it knows how to interpret both the search requests and
# the documents.
TEXT_SEARCH_LANG = "french"
