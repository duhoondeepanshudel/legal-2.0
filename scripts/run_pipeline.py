"""
Master Pipeline — Runs all steps sequentially to build the Legal Knowledge Graph.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

def run_pipeline():
    start = time.time()

    print("\n" + "=" * 60)
    print("  NYAYA GRAPH - Indian Legal Knowledge Graph Builder")
    print("=" * 60 + "\n")

    # Step 1: Generate Data
    from utils import print_banner
    print("Step 1/5: Generating legal judgment dataset...")
    import importlib
    mod1 = importlib.import_module("01_data_collector")
    mod1.generate_dataset()

    # Step 2: Extract Citations
    print("\nStep 2/5: Extracting case citations...")
    mod2 = importlib.import_module("02_citation_extractor")
    mod2.run_citation_extraction()

    # Step 3: Extract Judges
    print("\nStep 3/5: Extracting judge information...")
    mod3 = importlib.import_module("03_judge_extractor")
    mod3.run_judge_extraction()

    # Step 4: Extract Statutes
    print("\nStep 4/5: Extracting statute references...")
    mod4 = importlib.import_module("04_statute_extractor")
    mod4.run_statute_extraction()

    # Step 5: Build Graph
    print("\nStep 5/5: Building knowledge graph...")
    mod5 = importlib.import_module("05_graph_builder")
    mod5.build_graph()

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  PIPELINE COMPLETE - {elapsed:.1f} seconds")
    print("=" * 60)
    print("\nNext: Run the API server with:")
    print("  python api/server.py")
    print("\nThen open http://localhost:5000 in your browser.\n")


if __name__ == "__main__":
    run_pipeline()
