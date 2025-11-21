#!/usr/bin/env python3
"""
Quick script to create a test survey flow
"""
import json
from pathlib import Path

# Define a simple test survey
test_survey = {
    "version": "1.0.0",
    "start": "q1",
    "nodes": [
        {
            "id": "q1",
            "texts": ["Katera vrsta nepremičnine vas zanima?"],
            "choices": [
                {"title": "Stanovanje", "next": "q2"},
                {"title": "Hiša", "next": "q2"},
                {"title": "Poslovni prostor", "next": "q2"}
            ]
        },
        {
            "id": "q2",
            "texts": ["Prosimo vnesite vaš kontakt:"],
            "openInput": True,
            "inputType": "dual-contact",
            "next": "thanks"
        },
        {
            "id": "thanks",
            "texts": ["Hvala! Kmalu se oglasimo."],
            "terminal": True
        }
    ]
}

# Get path to conversation_flow.json
project_root = Path(__file__).parent.parent
flow_file = project_root / "data" / "conversation_flow.json"

# Backup old file
backup_file = project_root / "data" / "conversation_flow.json.backup"
if flow_file.exists():
    import shutil
    shutil.copy(flow_file, backup_file)
    print(f"✅ Backed up old flow to {backup_file}")

# Write new survey
with open(flow_file, "w", encoding="utf-8") as f:
    json.dump(test_survey, f, indent=2, ensure_ascii=False)

print(f"✅ Test survey written to {flow_file}")
print(f"Survey has {len(test_survey['nodes'])} questions")
print("You can now refresh the customer UI to see the survey")
