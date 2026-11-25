from app.utils import (
    CODE_OFFSET, base62_encode, code_for_id, is_valid_http_url, parse_user_agent, referrer_host,
)


def test_base62_known_values():
    assert base62_encode(0) == "0"
    assert base62_encode(61) == "Z"
    assert base62_encode(62) == "10"
    assert base62_encode(125) == "21"


def test_codes_are_unique_and_at_least_5_chars():
    codes = {code_for_id(i) for i in range(1, 5000)}
    assert len(codes) == 4999
    assert all(len(c) >= 5 for c in codes)
    assert len(base62_encode(CODE_OFFSET)) == 5


def test_url_validation():
    assert is_valid_http_url("https://example.com/a?b=1")
    assert is_valid_http_url("http://localhost:3000")
    assert not is_valid_http_url("javascript:alert(1)")
    assert not is_valid_http_url("ftp://example.com")
    assert not is_valid_http_url("example.com")
    assert not is_valid_http_url("https://")


def test_user_agent_parsing():
    iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit Mobile/15E148 Safari/604.1"
    assert parse_user_agent(iphone) == ("mobile", "Safari")
    chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    assert parse_user_agent(chrome) == ("desktop", "Chrome")
    edge = chrome + " Edg/120.0"
    assert parse_user_agent(edge) == ("desktop", "Edge")
    assert parse_user_agent("curl/8.0") == ("bot", "Other")
    assert parse_user_agent(None) == ("desktop", "Other")


def test_referrer_host():
    assert referrer_host("https://www.google.com/search?q=x") == "google.com"
    assert referrer_host("") is None
    assert referrer_host(None) is None
