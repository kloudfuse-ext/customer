#!/bin/bash

# Script to create users from CSV file
# CSV format expected: username,email

# Check if CSV file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <csv_file> [port]"
    echo "CSV format: username,email"
    echo "Default port: 8080"
    echo "Example: $0 users.csv"
    echo "Example with custom port: $0 users.csv 8080"
    exit 1
fi

CSV_FILE="$1"
PORT="${2:-8080}"

# Check if file exists
if [ ! -f "$CSV_FILE" ]; then
    echo "Error: File '$CSV_FILE' not found!"
    exit 1
fi

# Counter for tracking
SUCCESS_COUNT=0
FAIL_COUNT=0

echo "Starting user creation from $CSV_FILE..."
echo "Using endpoint: http://localhost:${PORT}/userinfo"
echo "----------------------------------------"

# Read CSV file line by line
while IFS=',' read -r username email || [[ -n "$username" ]]; do
    # Skip header line if it exists
    
    if [[ "$username" == "username" ]] && [[ "$email" == "email" ]]; then
        continue
    fi
    
    # Skip empty lines
    if [[ -z "$username" ]] || [[ -z "$email" ]]; then
        continue
    fi
    
    # Remove any whitespace
    username=$(echo "$username" | tr -d ' ')
    email=$(echo "$email" | tr -d ' ')
    
    echo -n "Creating user: $username ($email)... "
    
    # Execute curl command
    response=$(curl -s -X GET "http://localhost:${PORT}/userinfo" \
        -H "x-auth-request-user: $username" \
        -H "x-auth-request-email: $email" \
        -w "\n%{http_code}")
    
    # Extract HTTP status code
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo "SUCCESS"
        ((SUCCESS_COUNT++))
    else
        echo "FAILED (HTTP $http_code)"
        echo "  Response: $body"
        ((FAIL_COUNT++))
    fi
    
done < "$CSV_FILE"

echo "----------------------------------------"
echo "User creation completed!"
echo "Success: $SUCCESS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Total: $((SUCCESS_COUNT + FAIL_COUNT))"