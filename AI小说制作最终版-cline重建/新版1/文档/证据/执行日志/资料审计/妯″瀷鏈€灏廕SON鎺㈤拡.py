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
        "鍙繑鍥?JSON 瀵硅薄銆?,
        "杩斿洖涓€涓?JSON 瀵硅薄锛屽瓧娈?status 鐨勫€煎繀椤绘槸 ok銆備笉瑕佺敓鎴愭鏂囥€?,
    )
    print(json.dumps({"status": "passed", "response": response, "metadata": metadata}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
    raise
