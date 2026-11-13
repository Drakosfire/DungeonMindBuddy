"""Check PDF structure outside the Buddy API process before retaining bytes."""
import re
from subprocess import PIPE, SubprocessError, run


def validate_pdf_structure(body: bytes) -> None:
    if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)(?:\r|\n)", body):
        raise ValueError("Invalid PDF signature")
    try:
        result = run(
            ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--clearenv",
             "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
             "--ro-bind", "/lib64", "/lib64", "--dev", "/dev",
             "/usr/bin/pdfinfo", "-"],
            input=body, stdout=PIPE, stderr=PIPE, check=True, timeout=10,
        )
    except (OSError, SubprocessError) as exc:
        raise ValueError("Unable to validate PDF structure") from exc
    if result.stderr or not re.search(rb"^Pages:\s+[1-9]\d*\s*$", result.stdout, re.MULTILINE):
        raise ValueError("PDF has invalid structure or no pages")
    if not re.search(rb"^Encrypted:\s+no\s*$", result.stdout, re.MULTILINE):
        raise ValueError("Encrypted PDFs are unsupported")
