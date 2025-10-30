#!/bin/bash

# Fetch the list of realtime tables
echo "Fetching realtime tables..."
response=$(curl -s -X 'GET' \
  'http://localhost:9000/tables?type=realtime&sortAsc=true' \
  -H 'accept: application/json')

# Extract table names from JSON response
# Using jq if available, otherwise using grep/sed
if command -v jq &> /dev/null; then
    tables=$(echo "$response" | jq -r '.tables[]')
else
    # Fallback if jq is not installed
    tables=$(echo "$response" | grep -o '"kf_[^"]*"' | tr -d '"')
fi

# Check if we got any tables
if [ -z "$tables" ]; then
    echo "No tables found or error fetching tables"
    echo "Response: $response"
    exit 1
fi

echo "Found tables:"
echo "$tables"
echo ""

# Loop through each table and run resumeConsumption
for table in $tables; do
    # Remove _REALTIME suffix to get the base table name
    base_table="${table%_REALTIME}"

    echo "Resuming consumption for: $base_table (from $table)"
    curl -X 'POST' \
      "http://localhost:9000/tables/$base_table/resumeConsumption?consumeFrom=smallest" \
      -H 'accept: application/json' \
      -d ''
    echo ""
    echo "---"
done

echo "Done!"
