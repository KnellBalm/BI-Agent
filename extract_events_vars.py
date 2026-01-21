#!/usr/bin/env python3
"""
Extract detailed event and variable information from BI JSON files.
This focuses on eventList, varList, and other trigger mechanisms.
"""

import json
import base64
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from agents.bi_tool.visual_decoder import VisualDecoder


def extract_events_and_vars(file_path: str):
    """Extract eventList, varList, and other interactive elements."""

    print(f"\n{'='*80}")
    print(f"FILE: {Path(file_path).name}")
    print(f"{'='*80}\n")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    reports = data.get("report", [])

    for report in reports:
        print(f"## REPORT: {report.get('name', 'Unknown')}")
        print("-" * 80)

        if "etc" not in report or not report["etc"]:
            print("  No etc field found")
            continue

        try:
            decoded = VisualDecoder.decode_etc(report["etc"])

            # Extract varList (Parameters equivalent)
            print("\n### VARIABLE LIST (Parameters)")
            var_list = decoded.get("varList", [])
            if var_list:
                print(f"Total Variables: {len(var_list)}\n")
                for i, var in enumerate(var_list, 1):
                    print(f"  [{i}] Variable")
                    for key, value in var.items():
                        if isinstance(value, (str, int, float, bool)):
                            print(f"      {key}: {value}")
                        elif isinstance(value, list):
                            print(f"      {key}: [{len(value)} items]")
                        elif isinstance(value, dict):
                            print(f"      {key}: {{{len(value)} keys}}")
                    print()
            else:
                print("  (No variables found)\n")

            # Extract eventList (Actions equivalent)
            print("\n### EVENT LIST (Actions/Triggers)")
            event_list = decoded.get("eventList", [])
            if event_list:
                print(f"Total Events: {len(event_list)}\n")
                for i, event in enumerate(event_list, 1):
                    print(f"  [{i}] Event")
                    for key, value in event.items():
                        if isinstance(value, (str, int, float, bool)):
                            print(f"      {key}: {value}")
                        elif isinstance(value, list):
                            print(f"      {key}: [{len(value)} items]")
                            # Show first few items
                            for j, item in enumerate(value[:3], 1):
                                if isinstance(item, dict):
                                    print(f"        [{j}] {item}")
                        elif isinstance(value, dict):
                            print(f"      {key}: {{{len(value)} keys}}")
                            # Show the dict
                            for k, v in value.items():
                                print(f"        {k}: {v}")
                    print()
            else:
                print("  (No events found)\n")

            # Extract canvasFields (Field definitions)
            print("\n### CANVAS FIELDS")
            canvas_fields = decoded.get("canvasFields", [])
            if canvas_fields:
                print(f"Total Canvas Fields: {len(canvas_fields)}\n")
                for i, field in enumerate(canvas_fields[:10], 1):  # Show first 10
                    print(f"  [{i}] {field}")
            else:
                print("  (No canvas fields found)\n")

            # Extract exportFields
            print("\n### EXPORT FIELDS")
            export_fields = decoded.get("exportFields", [])
            if export_fields:
                print(f"Total Export Fields: {len(export_fields)}\n")
                for i, field in enumerate(export_fields[:10], 1):
                    print(f"  [{i}] {field}")
            else:
                print("  (No export fields found)\n")

            # Extract visual element interactions
            print("\n### VISUAL ELEMENT SAMPLES (First 10)")
            visuals = decoded.get("visual", [])
            if visuals:
                print(f"Total Visual Elements: {len(visuals)}\n")

                for i, vis in enumerate(visuals[:10], 1):
                    elem_id = vis.get("elementId", "N/A")
                    elem_type = vis.get("type", "N/A")
                    print(f"  [{i}] {elem_type} - {elem_id}")

                    # Check for event-related keys
                    event_keys = [k for k in vis.keys() if "event" in k.lower() or "click" in k.lower() or "action" in k.lower()]
                    if event_keys:
                        print(f"      Event Keys: {event_keys}")
                        for ek in event_keys:
                            print(f"        {ek}: {vis[ek]}")

                    # Check for filter-related keys
                    filter_keys = [k for k in vis.keys() if "filter" in k.lower()]
                    if filter_keys:
                        print(f"      Filter Keys: {filter_keys}")

                    # Show some key properties
                    if "datamodelId" in vis:
                        print(f"      DataModel ID: {vis['datamodelId']}")
                    if "text" in vis:
                        print(f"      Text: {vis['text']}")

                    print()
            else:
                print("  (No visual elements found)\n")

            # Extract groupMap
            print("\n### GROUP MAP")
            group_map = decoded.get("groupMap", {})
            if group_map:
                print(f"Total Groups: {len(group_map)}\n")
                for group_id, group_data in list(group_map.items())[:5]:
                    print(f"  Group ID: {group_id}")
                    print(f"    Data: {group_data}")
                    print()
            else:
                print("  (No groups found)\n")

        except Exception as e:
            print(f"ERROR decoding etc field: {e}")
            import traceback
            traceback.print_exc()


def main():
    files = [
        "/Users/zokr/python_workspace/BI-Agent/tmp/20260120.json",
        "/Users/zokr/python_workspace/BI-Agent/tmp/suwon_pop.json"
    ]

    for file_path in files:
        try:
            extract_events_and_vars(file_path)
        except FileNotFoundError:
            print(f"ERROR: File not found: {file_path}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
