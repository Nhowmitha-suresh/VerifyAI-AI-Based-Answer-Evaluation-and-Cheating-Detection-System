"""
AI Proctoring Suite - Top Level Entrypoint
Imports and executes the modular proctoring package.
"""

import sys
import os
import traceback



print("[PASS] Python Started", flush=True)

try:
    print("[PASS] Importing Proctor Main Module...", flush=True)
    from proctor.main import main
    print("[PASS] Proctor Main Module Imported Successfully", flush=True)
except Exception as e:
    print(f"[FAIL] Error importing proctor.main: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FAIL] Execution halted due to unhandled exception: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
