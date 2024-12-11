CREATE DATABASE lab_data;
\c lab_data
CREATE TABLE IF NOT EXISTS email_table (
    id SERIAL PRIMARY KEY,
    messageid TEXT UNIQUE,
    "date" TIMESTAMP,
    "from" TEXT,   -- "from" is a reserved keyword, so it needs to be quoted
    "to" TEXT,
    subject TEXT,
    cc TEXT,
    bcc TEXT,
    xfrom TEXT,
    xto TEXT,
    xcc TEXT,
    xbcc TEXT,
    xfolder TEXT,
    xorigin TEXT,
    xfilename TEXT,
    body TEXT
);
CREATE TABLE IF NOT EXISTS stg_email_table (
    messageid TEXT UNIQUE
);

