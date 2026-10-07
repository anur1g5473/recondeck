import re
import shlex

from .runner import run


class DigResult:
    def __init__(self, status=None, flags=None, answers=None, authority=None, error=None, timed_out=False, command=None, ok=False):
        self.status = status
        self.flags = flags or []
        self.answers = answers or []
        self.authority = authority or []
        self.error = error
        self.timed_out = timed_out
        self.command = command
        self.ok = ok

    def __repr__(self):
        return (
            f"DigResult(status={self.status!r}, flags={self.flags!r}, answers={len(self.answers)}, "
            f"authority={len(self.authority)}, error={self.error!r}, ok={self.ok!r})"
        )


def _clean_txt(value: str) -> str:
    return " ".join(value.replace('"', "").split())


def _parse_record_line(line: str):
    parts = line.split()
    if len(parts) < 5 or not parts[1].isdigit():
        return None
    name, ttl, record_class, rtype = parts[:4]
    rdata = " ".join(parts[4:])
    record = {
        "name": name.lower(),
        "ttl": int(ttl),
        "class": record_class,
        "type": rtype.upper(),
        "rdata": rdata,
        "rdata_lower": rdata.lower(),
    }
    if record["type"] == "TXT":
        record["rdata"] = _clean_txt(rdata)
        record["rdata_lower"] = record["rdata"].lower()
    return record


def _parse_dig_output(output: str, command_record):
    result = DigResult(command=command_record, timed_out=bool(command_record.timed_out))
    section = None

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        if line.startswith(";; ->>HEADER<<-"):
            match = re.search(r"status:\s*(\w+)", line, re.IGNORECASE)
            if match:
                result.status = match.group(1).upper()
            continue

        if line.startswith(";; flags:"):
            flag_text = line[len(";; flags:") :].split(";", 1)[0].strip()
            result.flags = flag_text.split() if flag_text else []
            continue

        if line.startswith(";; ANSWER SECTION:"):
            section = "answer"
            continue
        if line.startswith(";; AUTHORITY SECTION:"):
            section = "authority"
            continue
        if line.startswith(";;"):
            if any(token in line.lower() for token in [
                "connection timed out",
                "no servers could be reached",
                "communications error",
                "transfer failed",
            ]):
                result.error = line.strip()
            continue
        if line.startswith(";"):
            continue

        record = _parse_record_line(line)
        if record is None:
            continue
        if section == "authority":
            result.authority.append(record)
        else:
            result.answers.append(record)

    if result.status in {"NOERROR", "NXDOMAIN"} and result.error is None:
        result.ok = True
    else:
        result.ok = False

    if result.status is None and getattr(command_record, "tool_missing", False):
        result.error = (command_record.stderr or "tool not available").strip()
        result.ok = False

    return result


def dig_query(name, rtype, server=None, tcp=False, ipv6=False, norecurse=False, dnssec=False, chaos=False, extra=None):
    if extra is None:
        extra = []
    argv = ["dig"]
    if ipv6:
        argv.append("-6")
    if server:
        argv.append("@" + server)
    argv.extend([name, rtype])
    if chaos:
        argv.append("CH")
    argv.extend(["+noall", "+answer", "+authority", "+comments", "+time=3", "+tries=2"])
    if tcp:
        argv.append("+tcp")
    if norecurse:
        argv.append("+norecurse")
    if dnssec:
        argv.append("+dnssec")
    argv.extend(extra)

    command = run(argv=argv, timeout=5, stage="dig", label=f"{rtype} {name}")
    output = command.stdout + command.stderr
    result = _parse_dig_output(output, command)
    if command.timed_out:
        result.timed_out = True
    return result


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    qtype = sys.argv[2] if len(sys.argv) > 2 else "MX"
    print(dig_query(target, qtype))
