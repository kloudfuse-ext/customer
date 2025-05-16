#!/bin/bash

# create a dir for the table and run it from within that dir;
# it will dump a bunch of status files in case things go wrong we can use to track
# be careful on which controller you are connecting to
set -x
CONTROLLER=localhost:9000
TABLE=""

while :; do
    case "$1" in
        -t|--table)
            TABLE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-t|--table <table_name>] [-h|--help]"
            exit 0
            ;;
        "") # No more arguments
            break
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *) # Unexpected extra argument
            echo "Unexpected argument: $1"
            exit 1
            ;;
    esac
done

if [ -z "$TABLE" ]; then
    echo "Error: Table name is required. Use -t or --table to specify the table name."
    exit 1
fi

# Get a list of segments for a table
curl -s "http://${CONTROLLER}/tables/${TABLE}_REALTIME/segmentsStatus" > "${TABLE}.new"
echo "Total segments:"
cat "${TABLE}.new" | jq '.[].segmentName' | wc -l

# Filter out good segments
cat "${TABLE}.new" | jq '.[] | select(.segmentStatus != "GOOD") | .segmentName' | sed s'/"//'g > "${TABLE}.bad"
echo "Deleting !GOOD segments:"
wc -l "${TABLE}.bad"

echo -n "Press enter to proceed or ^C to cancel"
read ans

# Fetch segment status
for seg in `cat "${TABLE}.bad"`; do
    curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/$seg/metadata?columns=\*" > "${seg}.status"
    cat "${seg}.status"
    #read ans
    echo " deleting ${seg}"
    curl -s "http://${CONTROLLER}/segments/${TABLE}_REALTIME/$seg" -X 'DELETE'
done
