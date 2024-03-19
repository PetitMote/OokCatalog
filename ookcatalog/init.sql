CREATE TYPE pgeasycatalog_month AS ENUM (
    'Janvier',
    'Février',
    'Mars',
    'Avril',
    'Mai',
    'Juin',
    'Juillet',
    'Août',
    'Septembre',
    'Octobre',
    'Novembre',
    'Décembre'
);

CREATE TABLE public.pgeasycatalog (
  table_schema TEXT NOT NULL,
  table_name TEXT NOT NULL,
  description_long TEXT,
  update_months PGEASYCATALOG_MONTH[],
  PRIMARY KEY (table_schema, table_name)
);

ALTER TABLE public.pgeasycatalog OWNER TO pgeasycatalog;