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

create table public.pgeasycatalog (
  table_schema text not null,
  table_name text not null,
  description_long text,
  update_months pgeasycatalog_month[],
  primary key (table_schema, table_name)
);

