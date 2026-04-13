#!/usr/bin/env python3

import argparse
import json
import os
import requests
import sys

def get_segments_status(controller, table):
    url = "http://{}/tables/{}/segmentsStatus".format(controller, table)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error: Failed to get segments status - {}".format(e))
        sys.exit(1)

def get_segment_metadata(controller, table, segment):
    url = "http://{}/segments/{}/{}/metadata?columns=*".format(controller, table, segment)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error: Failed to get segment metadata - {}".format(e))
        return None

def delete_segment(controller, table, segment):
    url = "http://{}/segments/{}/{}".format(controller, table, segment)
    try:
        response = requests.delete(url, timeout=30)
        return response
    except requests.exceptions.RequestException as e:
        print("Error: Failed to delete segment - {}".format(e))
        return None

def get_all_tables(controller):
    url = "http://{}/tables".format(controller)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("tables", [])
    except requests.exceptions.RequestException as e:
        print("Error: Failed to get tables list - {}".format(e))
        sys.exit(1)

def process_table(controller, table):
    print("\n" + "=" * 60)
    print("Processing table: {}".format(table))
    print("=" * 60)

    segments_status = get_segments_status(controller, table)
    print("Total segments: {}".format(len(segments_status)))

    bad_segments = []
    for segment_info in segments_status:
        if segment_info.get("segmentStatus") != "GOOD":
            bad_segments.append(segment_info.get("segmentName"))

    if len(bad_segments) == 0:
        print("No bad segments found.")
        return 0

    print("Total Bad segments: {}".format(len(bad_segments)))
    for seg in bad_segments:
        metadata = get_segment_metadata(controller, table, seg)
        if metadata:
            print(json.dumps(metadata, indent=2))

        print(" deleting {}".format(seg))
    return len(bad_segments)

def main():
    parser = argparse.ArgumentParser(description="Delete bad Pinot segments for a table")
    parser.add_argument("-c", "--controller", default="pinot-controller:9000", help="Pinot controller host:port (default: pinot-controller:9000)")

    args = parser.parse_args()

    controller = args.controller

    print("Fetching all tables from controller: {}".format(controller))
    tables = get_all_tables(controller)
    print("Found {} tables".format(len(tables)))

    total_bad_segments = 0
    for table in tables:
        bad_count = process_table(controller, table)
        total_bad_segments += bad_count

    print("\n" + "=" * 60)
    print("SUMMARY: Total bad segments across all tables: {}".format(total_bad_segments))
    print("=" * 60)

    print("\nDONE.")

if __name__ == "__main__":
    main()