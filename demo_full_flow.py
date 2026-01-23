"""demo_full_flow.py
Complete MVP flow demonstration:
Data Profiling -> Interaction Suggestion -> Theme Injection -> JSON Generation
"""
import os
import json
import pandas as pd
from backend.agents.data_source.profiler import DataProfiler
from backend.orchestrator.interaction_orchestrator import InteractionOrchestrator

def run_demo():
    print("🚀 Starting BI-Agent Full Flow Demo...")

    # 1. Prepare Mock Data (Population Data)
    data = {
        "REFERENCEDATE": ["2023.01", "2023.02", "2023.03", "2023.01", "2023.02", "2023.03"],
        "REGION": ["Seoul", "Seoul", "Seoul", "Busan", "Busan", "Busan"],
        "POPULATION": [940, 941, 939, 330, 331, 329],
        "MALE": [460, 461, 460, 160, 161, 160],
        "FEMALE": [480, 480, 479, 170, 170, 169]
    }
    df = pd.DataFrame(data)
    
    # 2. Profiling
    print("📊 Profiling data...")
    profiler = DataProfiler(df)
    profile = profiler.profile()
    
    # 3. Create Orchestrator (Ties InteractionLogic, InHouseGenerator, ThemeEngine)
    orchestrator = InteractionOrchestrator()
    
    # 4. Generate Dashboard
    print("🛠️ Generating Automated Interactive Dashboard...")
    result = orchestrator.handle_interactive_trigger(params={}, profile=profile)
    
    if result["status"] == "success":
        output_path = result["path"]
        print(f"✅ Success! Dashboard generated at: {output_path}")
        
        # Read and print a summary of the generated JSON
        with open(output_path, "r", encoding="utf-8") as f:
            dashboard = json.load(f)
            
        report = dashboard["report"][0]
        print("\n--- Dashboard Summary ---")
        print(f"Title: {report['name']}")
        print(f"Variables: {[v['name'] for v in report['varList']]}")
        print(f"Visuals: {[v['id'] for v in report['visual']]}")
        print(f"Styles: {report['visual'][0].get('style', {}).get('textColor')} (Color scheme applied)")
        print(f"Query Template: {dashboard['datamodel'][0]['dataset']['query']}")
        print("--------------------------")
    else:
        print("❌ Generation failed.")

if __name__ == "__main__":
    run_demo()
