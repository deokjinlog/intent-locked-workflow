from pathlib import Path
from scripts.detect_auth import detect_auth_pattern


def test_detect_jwt_login(tmp_path: Path):
    (tmp_path / "auth.py").write_text(
        "@router.post('/auth/login')\ndef login(...): return {'access_token': ...}\n",
        encoding="utf-8",
    )
    assert detect_auth_pattern(tmp_path).pattern == "jwt-login"


def test_detect_static_env_token(tmp_path: Path):
    (tmp_path / "client.py").write_text(
        "API_TOKEN = os.environ['API_TOKEN']\nheaders={'Authorization': f'Bearer {API_TOKEN}'}\n",
        encoding="utf-8",
    )
    assert detect_auth_pattern(tmp_path).pattern == "static-env-token"


def test_unknown_when_no_signal(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    assert detect_auth_pattern(tmp_path).pattern == "unknown"
