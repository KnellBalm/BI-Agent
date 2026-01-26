#!/usr/bin/env python3
"""
BI JSON Analysis Script
Extracts and analyzes data source queries and trigger mechanisms from BI solution JSON files.
"""

import json
import base64
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from agents.bi_tool.json_parser import BIJsonParser
from agents.bi_tool.visual_decoder import VisualDecoder


def analyze_connectors(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze database connector configurations."""
    connectors = data.get("connector", [])

    analysis = {
        "count": len(connectors),
        "connectors": []
    }

    for conn in connectors:
        conn_info = {
            "id": conn.get("id", "N/A"),
            "name": conn.get("name", "N/A"),
            "type": conn.get("type", "N/A"),
            "has_config": "config" in conn,
        }

        # Don't expose sensitive info
        if "config" in conn:
            config = conn["config"]
            conn_info["config_keys"] = list(config.keys())

        analysis["connectors"].append(conn_info)

    return analysis


def analyze_datamodels(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze data models, queries, and dependencies."""
    datamodels = data.get("datamodel", [])

    analysis = {
        "count": len(datamodels),
        "datamodels": [],
        "dependencies": [],
        "query_patterns": []
    }

    for dm in datamodels:
        dm_info = {
            "id": dm.get("id", "N/A"),
            "name": dm.get("name", "N/A"),
            "connector_id": dm.get("connector_id", "N/A"),
            "referenced_id": dm.get("referenced_id", "N/A"),
            "field_count": len(dm.get("fields", [])),
            "fields": [f.get("name") for f in dm.get("fields", [])],
        }

        # Extract query
        if "dataset" in dm and "query" in dm["dataset"]:
            query = dm["dataset"]["query"]
            dm_info["query"] = query

            # Analyze query pattern
            if "| sql" in query:
                analysis["query_patterns"].append("DSL with SQL")
            if "| calculate" in query:
                analysis["query_patterns"].append("DSL with calculation")

        analysis["datamodels"].append(dm_info)

        # Track dependencies
        if dm.get("referenced_id"):
            analysis["dependencies"].append({
                "source": dm.get("name"),
                "source_id": dm.get("id"),
                "references": dm.get("referenced_id")
            })

    return analysis


def analyze_visuals(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze visual configurations."""
    visuals = data.get("visual", [])

    analysis = {
        "count": len(visuals),
        "visuals": []
    }

    for vis in visuals:
        vis_info = {
            "id": vis.get("id", "N/A"),
            "name": vis.get("name", "N/A"),
            "type": vis.get("type", "N/A"),
            "has_etc": "etc" in vis,
        }

        # Decode etc field if present
        if "etc" in vis and vis["etc"]:
            try:
                decoded = VisualDecoder.decode_etc(vis["etc"])
                vis_info["decoded_keys"] = list(decoded.keys())
                vis_info["decoded_sample"] = {
                    k: str(v)[:100] if len(str(v)) > 100 else v
                    for k, v in list(decoded.items())[:3]
                }
            except Exception as e:
                vis_info["decode_error"] = str(e)

        analysis["visuals"].append(vis_info)

    return analysis


def analyze_reports(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze report configurations and dashboard actions."""
    reports = data.get("report", [])

    analysis = {
        "count": len(reports),
        "reports": []
    }

    for report in reports:
        report_info = {
            "id": report.get("id", "N/A"),
            "name": report.get("name", "N/A"),
            "has_etc": "etc" in report,
        }

        # Decode etc field to find visual elements and actions
        if "etc" in report and report["etc"]:
            try:
                decoded = VisualDecoder.decode_etc(report["etc"])
                report_info["decoded_keys"] = list(decoded.keys())

                # Extract visual elements (potential action targets)
                if "visual" in decoded:
                    visuals = decoded["visual"]
                    report_info["visual_count"] = len(visuals)
                    report_info["visual_elements"] = [
                        {
                            "elementId": v.get("elementId", "N/A"),
                            "type": v.get("type", "N/A"),
                            "has_text": "text" in v,
                            "keys": list(v.keys())
                        }
                        for v in visuals[:5]  # Sample first 5
                    ]

                # Look for action-like properties
                if "dashboard" in decoded:
                    report_info["has_dashboard_config"] = True

            except Exception as e:
                report_info["decode_error"] = str(e)

        analysis["reports"].append(report_info)

    return analysis


def find_trigger_mechanisms(data: Dict[str, Any]) -> Dict[str, Any]:
    """Identify Tableau-equivalent trigger mechanisms."""

    mechanisms = {
        "parameters": [],
        "sets": [],
        "actions": [],
        "filters": []
    }

    # Check datamodels for parameter-like references
    for dm in data.get("datamodel", []):
        if dm.get("referenced_id"):
            mechanisms["parameters"].append({
                "type": "data_reference",
                "source": dm.get("name"),
                "target_id": dm.get("referenced_id"),
                "description": f"Data model '{dm.get('name')}' references another model"
            })

        # Check if query has parameterized elements
        if "dataset" in dm and "query" in dm["dataset"]:
            query = dm["dataset"]["query"]
            if "WHERE" in query.upper() or "?" in query:
                mechanisms["filters"].append({
                    "type": "query_filter",
                    "datamodel": dm.get("name"),
                    "query": query
                })

    # Check visuals for action-like configurations
    for vis in data.get("visual", []):
        if "etc" in vis and vis["etc"]:
            try:
                decoded = VisualDecoder.decode_etc(vis["etc"])

                # Look for interaction configs
                if any(key in decoded for key in ["onClick", "onHover", "action", "interaction"]):
                    mechanisms["actions"].append({
                        "type": "visual_interaction",
                        "visual_name": vis.get("name"),
                        "interaction_keys": [k for k in decoded.keys() if "click" in k.lower() or "action" in k.lower()]
                    })
            except:
                pass

    # Check reports for dashboard actions
    for report in data.get("report", []):
        if "etc" in report and report["etc"]:
            try:
                decoded = VisualDecoder.decode_etc(report["etc"])

                if "visual" in decoded:
                    # Visual elements can be targets of actions
                    element_ids = [v.get("elementId") for v in decoded["visual"] if v.get("elementId")]
                    if element_ids:
                        mechanisms["actions"].append({
                            "type": "dashboard_elements",
                            "report_name": report.get("name"),
                            "element_count": len(element_ids),
                            "element_ids": element_ids[:10]  # Sample
                        })
            except:
                pass

    return mechanisms


def generate_dependency_graph(datamodels: List[Dict[str, Any]]) -> str:
    """Generate a text-based dependency graph."""

    # Build id to name mapping
    id_to_name = {dm.get("id"): dm.get("name") for dm in datamodels}

    graph_lines = ["## Data Model Dependency Graph\n"]

    for dm in datamodels:
        name = dm.get("name", "Unknown")
        ref_id = dm.get("referenced_id")

        if ref_id:
            ref_name = id_to_name.get(ref_id, f"[{ref_id[:8]}...]")
            graph_lines.append(f"  {name}")
            graph_lines.append(f"    └─→ references: {ref_name}")
        else:
            graph_lines.append(f"  {name} (standalone)")

    return "\n".join(graph_lines)


def main():
    """Main analysis function."""

    files = [
        "/Users/zokr/python_workspace/BI-Agent/tmp/20260120.json",
        "/Users/zokr/python_workspace/BI-Agent/tmp/suwon_pop.json"
    ]

    for file_path in files:
        print(f"\n{'='*80}")
        print(f"ANALYZING: {Path(file_path).name}")
        print(f"{'='*80}\n")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Top-level structure
            print("## Top-Level Structure")
            print(f"  - connector: {len(data.get('connector', []))} items")
            print(f"  - datamodel: {len(data.get('datamodel', []))} items")
            print(f"  - visual: {len(data.get('visual', []))} items")
            print(f"  - report: {len(data.get('report', []))} items")
            print(f"  - image: {len(data.get('image', []))} items")
            print()

            # Analyze connectors
            print("## 1. DATA SOURCE CONNECTORS")
            print("-" * 80)
            connector_analysis = analyze_connectors(data)
            print(f"Total Connectors: {connector_analysis['count']}\n")
            for conn in connector_analysis['connectors']:
                print(f"  [{conn['type']}] {conn['name']}")
                print(f"    ID: {conn['id']}")
                if conn['has_config']:
                    print(f"    Config Keys: {', '.join(conn['config_keys'])}")
                print()

            # Analyze datamodels
            print("\n## 2. DATA MODELS AND QUERIES")
            print("-" * 80)
            datamodel_analysis = analyze_datamodels(data)
            print(f"Total Data Models: {datamodel_analysis['count']}\n")

            for dm in datamodel_analysis['datamodels'][:10]:  # Show first 10
                print(f"  [{dm['name']}]")
                print(f"    ID: {dm['id']}")
                print(f"    Connector: {dm['connector_id']}")
                if dm['referenced_id']:
                    print(f"    References: {dm['referenced_id']}")
                print(f"    Fields ({dm['field_count']}): {', '.join(dm['fields'][:5])}")
                if 'query' in dm:
                    print(f"    Query: {dm['query'][:150]}...")
                print()

            if len(datamodel_analysis['datamodels']) > 10:
                print(f"  ... and {len(datamodel_analysis['datamodels']) - 10} more data models\n")

            # Dependency graph
            print("\n## 3. DATA MODEL DEPENDENCIES")
            print("-" * 80)
            print(generate_dependency_graph(data.get('datamodel', [])))
            print()

            # Analyze visuals
            print("\n## 4. VISUAL CONFIGURATIONS")
            print("-" * 80)
            visual_analysis = analyze_visuals(data)
            print(f"Total Visuals: {visual_analysis['count']}\n")

            for vis in visual_analysis['visuals'][:5]:  # Show first 5
                print(f"  [{vis['type']}] {vis['name']}")
                print(f"    ID: {vis['id']}")
                if 'decoded_keys' in vis:
                    print(f"    Config Keys: {', '.join(vis['decoded_keys'])}")
                print()

            # Analyze reports
            print("\n## 5. REPORTS AND DASHBOARDS")
            print("-" * 80)
            report_analysis = analyze_reports(data)
            print(f"Total Reports: {report_analysis['count']}\n")

            for rep in report_analysis['reports']:
                print(f"  {rep['name']}")
                print(f"    ID: {rep['id']}")
                if 'decoded_keys' in rep:
                    print(f"    Config Keys: {', '.join(rep['decoded_keys'])}")
                if 'visual_count' in rep:
                    print(f"    Visual Elements: {rep['visual_count']}")
                    if 'visual_elements' in rep:
                        for elem in rep['visual_elements'][:3]:
                            print(f"      - [{elem['type']}] {elem['elementId']}")
                print()

            # Find trigger mechanisms
            print("\n## 6. TRIGGER MECHANISMS (Parameters, Sets, Actions)")
            print("-" * 80)
            mechanisms = find_trigger_mechanisms(data)

            print(f"\n### Parameters (Data References)")
            if mechanisms['parameters']:
                for param in mechanisms['parameters']:
                    print(f"  - {param['description']}")
                    print(f"    Source: {param['source']}")
                    print(f"    Target ID: {param['target_id']}")
            else:
                print("  (None found)")

            print(f"\n### Filters (Query-based)")
            if mechanisms['filters']:
                for filt in mechanisms['filters']:
                    print(f"  - Datamodel: {filt['datamodel']}")
                    print(f"    Query: {filt['query'][:100]}...")
            else:
                print("  (None found)")

            print(f"\n### Actions (Visual Interactions)")
            if mechanisms['actions']:
                for action in mechanisms['actions']:
                    print(f"  - Type: {action['type']}")
                    if action['type'] == 'dashboard_elements':
                        print(f"    Report: {action['report_name']}")
                        print(f"    Elements: {action['element_count']}")
            else:
                print("  (None found)")

            print("\n")

        except FileNotFoundError:
            print(f"ERROR: File not found: {file_path}")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {file_path}: {e}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
