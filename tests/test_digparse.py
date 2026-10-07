from pathlib import Path

from recondeck.digparse import _parse_dig_output, DigResult
from recondeck.runner import CommandRecord

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _record(label: str = "test"):
    return CommandRecord(
        id="cmd-1",
        stage="dig",
        label=label,
        argv=["dig", "example.com", "MX"],
        command_line="dig example.com MX",
        started_at="2024-01-01T00:00:00Z",
        duration_ms=12,
    )


def _load(name: str):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_normal_answer_fixture():
    result = _parse_dig_output(_load("normal_answer.txt"), _record("normal answer"))
    assert result.status == "NOERROR"
    assert result.flags == ["qr", "rd", "ra"]
    assert result.answers[0]["type"] == "MX"
    assert result.answers[0]["rdata"] == "10 mail.example.com."
    assert result.ok is True


def test_nxdomain_fixture():
    result = _parse_dig_output(_load("nxdomain.txt"), _record("nxdomain"))
    assert result.status == "NXDOMAIN"
    assert result.ok is True


def test_servfail_fixture():
    result = _parse_dig_output(_load("servfail.txt"), _record("servfail"))
    assert result.status == "SERVFAIL"
    assert result.ok is False


def test_refused_fixture():
    result = _parse_dig_output(_load("refused.txt"), _record("refused"))
    assert result.status == "REFUSED"
    assert result.ok is False


def test_timeout_fixture_sets_error_and_false_ok():
    result = _parse_dig_output(_load("timeout.txt"), _record("timeout"))
    assert result.error is not None
    assert "timed out" in result.error.lower()
    assert result.ok is False


def test_multi_chunk_txt_fixture():
    result = _parse_dig_output(_load("txt_multi_chunk.txt"), _record("txt"))
    assert result.answers[0]["type"] == "TXT"
    assert result.answers[0]["rdata"] == "v=spf1 include:_spf.example.com ~all"


def test_cname_chain_fixture():
    result = _parse_dig_output(_load("cname_chain.txt"), _record("cname"))
    assert result.answers[0]["type"] == "CNAME"
    assert result.answers[1]["type"] == "A"
    assert result.answers[0]["rdata"] == "www2.example.com."


def test_axfr_success_fixture():
    result = _parse_dig_output(_load("axfr_success.txt"), _record("axfr"))
    assert result.status == "NOERROR"
    assert len(result.answers) >= 2


def test_axfr_refused_fixture():
    result = _parse_dig_output(_load("axfr_refused.txt"), _record("axfr_refused"))
    assert result.status == "REFUSED"
    assert result.ok is False
