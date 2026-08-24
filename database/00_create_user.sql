-- =============================================================================
-- NEXUS-SQL | 00_create_user.sql
-- Layer: BOOTSTRAP  –  Run as SYS or a DBA-privileged account ONCE.
-- Creates the application schema owner with the minimum required privileges.
-- =============================================================================

-- Adjust password before running in any environment.
CREATE USER nexus_sql_app IDENTIFIED BY "NexusSQL_Dev_2024#"
    DEFAULT TABLESPACE users
    TEMPORARY TABLESPACE temp
    QUOTA UNLIMITED ON users;

-- Minimum session / DDL privileges
GRANT CREATE SESSION      TO nexus_sql_app;
GRANT CREATE TABLE        TO nexus_sql_app;
GRANT CREATE VIEW         TO nexus_sql_app;
GRANT CREATE MATERIALIZED VIEW TO nexus_sql_app;
GRANT CREATE SEQUENCE     TO nexus_sql_app;
GRANT CREATE PROCEDURE    TO nexus_sql_app;
GRANT CREATE TRIGGER      TO nexus_sql_app;
GRANT CREATE INDEX        TO nexus_sql_app;
GRANT CREATE TYPE         TO nexus_sql_app;

-- Vector search (Oracle 23ai)
-- Comment out if running on Oracle 21c or earlier.
GRANT DB_DEVELOPER_ROLE   TO nexus_sql_app;

PROMPT User nexus_sql_app created successfully.
PROMPT Connect as nexus_sql_app and run 01_schema.sql next.
