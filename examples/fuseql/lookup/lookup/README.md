# lookup

Retrieves fields from a pre-defined lookup table and adds them to log query results by matching on one or more key fields. Use `lookup` to enrich log data with external context — for example, adding user geography from a locations table or expanding error codes into descriptions.

## Syntax

```fuseql
| lookup <table_field> as <alias>[, <table_field2> as <alias2>, ...]
    from "<table_name>"
    on <log_field> = <table_key>[, <log_field2> = <table_key2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<table_field> as <alias>` | Required | Fields to retrieve from the lookup table, each with an output alias. |
| `from "<table_name>"` | Required | Name of the lookup table created in the Kloudfuse UI. |
| `on <log_field> = <table_key>` | Required | Join condition: log field matched to lookup table primary key. |

## Example

Enrich nginx access logs with user country and city from the `UserLocations` table.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| lookup country as userCountry, city as userCity
    from "UserLocations"
    on userId = userID
| count as requests by userCountry
```

**Expected output (illustrative):**

| userCountry | requests |
|---|---|
| United States | 842,301 |
| Germany | 97,443 |
| Japan | 54,812 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | lookup country as userCountry, city as userCity from \\\"UserLocations\\\" on userId = userID | count as requests by userCountry\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Create and populate lookup tables in the Kloudfuse UI before referencing them in queries.
- Maximum lookup table size: 50 MB.
- Rows with no matching key in the lookup table are dropped (left-join semantics not supported).
- Join conditions must use compatible data types and the table's primary key(s).
