"""
Shared utilities for the Legal Knowledge Graph pipeline.
"""
import os
import json
import re
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Ensure directories exist
for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR]:
    os.makedirs(d, exist_ok=True)


def load_json(filepath):
    """Load a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filepath):
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"[OK] Saved: {filepath}")


def normalize_case_name(name):
    """Normalize case names for matching."""
    name = re.sub(r'\s+', ' ', name.strip())
    name = re.sub(r'\bvs\.?\b', 'vs', name, flags=re.IGNORECASE)
    return name.strip()


def normalize_judge_name(name):
    """Normalize judge names."""
    name = re.sub(r'^(Hon\'?ble\s+|Justice\s+|J\.\s*)', '', name.strip(), flags=re.IGNORECASE)
    name = re.sub(r'\s*,?\s*J\.?\s*$', '', name)
    name = re.sub(r'\s+', ' ', name.strip())
    return name.strip()


def normalize_statute(text):
    """Normalize statute references."""
    text = re.sub(r'\s+', ' ', text.strip())
    return text


def get_timestamp():
    """Get current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_banner(title):
    """Print a formatted banner."""
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width + "\n")


def print_stats(stats_dict):
    """Print statistics in a formatted way."""
    for key, value in stats_dict.items():
        print(f"  {key}: {value}")
    print()
