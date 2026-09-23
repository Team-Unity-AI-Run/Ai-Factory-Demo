import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scan_code import scan_file  # noqa: E402


def test_detects_hardcoded_password(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('password = "admin123"\n')
    findings = scan_file(str(f))
    assert any(x["issue"] == "Hardcoded password" for x in findings)
    assert findings[0]["severity"] == "HIGH"


def test_detects_api_key(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('api_key = "sk-12345"\n')
    findings = scan_file(str(f))
    assert any(x["issue"] == "Hardcoded API key or secret" for x in findings)


def test_detects_debug_print(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('print("debug value")\n')
    findings = scan_file(str(f))
    assert any(x["issue"] == "Debug print statement" for x in findings)


def test_detects_dangerous_shell(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("import os\nos.system(user_input)\n")
    findings = scan_file(str(f))
    assert any(x["issue"] == "Dangerous shell/eval/exec usage" for x in findings)


def test_clean_file_has_no_findings(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    findings = scan_file(str(f))
    assert findings == []


def test_findings_are_json_serializable(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('password = "x"\n')
    findings = scan_file(str(f))
    json.dumps(findings)  # should not raise
