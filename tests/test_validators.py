import pytest

from recondeck.validators import parse_target


def test_parse_target_accepts_standard_hostname():
    data = parse_target("https://www.vit.ac.in/some/page?x=1")
    assert data["hostname"] == "www.vit.ac.in"
    assert data["registered_domain"] == "vit.ac.in"
    assert data["suffix"] == "ac.in"


def test_parse_target_accepts_trailing_dot_and_idna():
    data = parse_target("xn--bcher-kva.example.")
    assert data["hostname"] == "xn--bcher-kva.example"
    assert data["registered_domain"] == "xn--bcher-kva.example"


def test_parse_target_rejects_ip_address_and_local_names():
    with pytest.raises(ValueError):
        parse_target("127.0.0.1")
    with pytest.raises(ValueError):
        parse_target("localhost")
    with pytest.raises(ValueError):
        parse_target("example.local")


def test_parse_target_rejects_bad_input():
    with pytest.raises(ValueError):
        parse_target("")
    with pytest.raises(ValueError):
        parse_target("-evil.com")
    with pytest.raises(ValueError):
        parse_target("example.com;rm -rf /")
