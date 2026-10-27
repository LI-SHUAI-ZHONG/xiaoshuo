import json
import importlib.util
import sys
from pathlib import Path
root = Path(sys.argv[1])
model_path = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("project_text_generation_model", model_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    response, metadata = module.generate_json(
        root,
        "Return only a JSON object.",
        "Return a JSON object with status set to ok. Do not generate prose.",
    )
    print(json.dumps({"status": "passed", "response": response, "metadata": metadata}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
    raise
