SECRET_KEY = "<KEY>"  # As of now, OokCatalog does not make use of any cookie
DATABASE = {  # Configure database access with your actual connexion parameter
    "HOST": "localhost",
    "PORT": "5432",
    "DBNAME": "ookcatalog",
    "USER": "ookcatalog",
    "PASSWORD": "password",
}
DATABASE_TITLE = "BDU"  # Title / name of your database. For now, only used for decoration / clarity for your users.
# Language passed to PostgreSQL for full text search. Needed so it knows how to interpret both the search requests and
# the documents.
TEXT_SEARCH_LANG = "french"
