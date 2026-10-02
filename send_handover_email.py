#!/usr/bin/env python3
"""
Send the flood-mapping handover letter by email.

The Gmail app password is prompted for at run time via getpass -- it is never
stored, logged, or written to disk. Use a Google **App Password** (Google
Account > Security > 2-Step Verification > App passwords), not your normal
account password; Gmail rejects the account password for SMTP.

    python send_handover_email.py                 # preview only, sends nothing
    python send_handover_email.py --send          # prompts, confirms, then sends
    python send_handover_email.py --send --attach-data   # also attach the 5.6 MB zip

Edit FROM_ADDRESS / TO / CC below if the recipients change.
"""
import argparse, getpass, mimetypes, os, re, smtplib, ssl, sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

FROM_NAME    = "Trevor Monroe"
FROM_ADDRESS = "trevmon28@gmail.com"
TO           = ["tmonroe@worldbank.org"]
CC           = []
SUBJECT      = ("Eastern DRC flood mapping - updated dataset "
                "(Jan 2025 - Jul 2026); area ranking has changed")

ROOT        = Path(__file__).resolve().parent
LETTER_PATH = ROOT / "docs" / "handover_letter.md"
DATA_ZIP    = ROOT / "data" / "eastern_drc_flood_data.zip"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 587

# Greeting left neutral on purpose: do not guess the recipient's name from the
# address. Personalise this line before sending if you want to.
INTRO = """Hi,

Below is the handover letter for the updated eastern DRC flood extent dataset.

The short version: it is built to tell you which areas flood most, and that ranking
has changed since the last version. Mambasa and Rutshuru are now first and second;
Irumu, previously first by a wide margin, drops to third after we found a sensor
calibration mismatch that had inflated it. Mambasa is the best-evidenced area in the
series - both of its flood months are confirmed by an independent disaster registry.

Treat the square-kilometre figures as indicative rather than measured. Every file is
linked at the bottom of the letter, so nothing needs to be attached.

Happy to walk through any of it.

Trevor

---

"""


def md_to_text(md: str) -> str:
    """Flatten the markdown into something readable in a plain-text client."""
    out = []
    for line in md.splitlines():
        if line.strip() == "---":
            out.append("-" * 70); continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"`(.+?)`", r"\1", line)
        out.append(line)
    return "\n".join(out)


def md_to_html(md: str) -> str:
    """Minimal markdown -> HTML. Handles headings, tables, bold, code, lists."""
    html, in_table, in_list = [], False, False
    for line in md.splitlines():
        s = line.rstrip()
        if re.match(r"^\|[\s:-]+\|$", s.replace("-", "-")) and set(s) <= set("|-: "):
            continue                                        # table rule
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not in_table:
                html.append('<table cellpadding="6" cellspacing="0" '
                            'style="border-collapse:collapse;border:1px solid #ccc">')
                in_table = True
                html.append("<tr>" + "".join(
                    f'<th style="border:1px solid #ccc;text-align:left;background:#f4f4f4">{c}</th>'
                    for c in cells) + "</tr>")
                continue
            html.append("<tr>" + "".join(
                f'<td style="border:1px solid #ccc">{c}</td>' for c in cells) + "</tr>")
            continue
        if in_table:
            html.append("</table>"); in_table = False
        if s.startswith("- "):
            if not in_list: html.append("<ul>"); in_list = True
            html.append(f"<li>{s[2:]}</li>"); continue
        if in_list:
            html.append("</ul>"); in_list = False
        if s.strip() == "---":
            html.append("<hr>"); continue
        m = re.match(r"^(#{1,6})\s*(.+)$", s)
        if m:
            lvl = len(m.group(1)); html.append(f"<h{lvl}>{m.group(2)}</h{lvl}>"); continue
        html.append(f"<p>{s}</p>" if s.strip() else "")
    if in_table: html.append("</table>")
    if in_list: html.append("</ul>")
    body = "\n".join(html)
    for pat, rep in ((r"\*\*(.+?)\*\*", r"<strong>\1</strong>"),
                     (r"`(.+?)`", r"<code>\1</code>")):
        body = re.sub(pat, rep, body)
    return ('<html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;'
            'font-size:14px;line-height:1.5;color:#222">' + body + "</body></html>")


def build(attach_data: bool) -> EmailMessage:
    if not LETTER_PATH.exists():
        sys.exit(f"Letter not found: {LETTER_PATH}")
    md = LETTER_PATH.read_text(encoding="utf-8")

    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{FROM_ADDRESS}>"
    msg["To"] = ", ".join(TO)
    if CC: msg["Cc"] = ", ".join(CC)
    msg["Subject"] = SUBJECT
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(INTRO + md_to_text(md))
    msg.add_alternative(md_to_html(INTRO.replace("\n", "\n\n") + md), subtype="html")

    msg.add_attachment(md.encode("utf-8"), maintype="text", subtype="markdown",
                       filename="handover_letter.md")
    if attach_data:
        if not DATA_ZIP.exists():
            sys.exit(f"Data zip not found: {DATA_ZIP} (run build_handover.py first)")
        size_mb = DATA_ZIP.stat().st_size / 1e6
        if size_mb > 24:
            sys.exit(f"Data zip is {size_mb:.1f} MB; Gmail caps attachments near 25 MB. "
                     "Share it via a link instead.")
        ctype, _ = mimetypes.guess_type(DATA_ZIP.name)
        maintype, subtype = (ctype or "application/zip").split("/", 1)
        msg.add_attachment(DATA_ZIP.read_bytes(), maintype=maintype, subtype=subtype,
                           filename=DATA_ZIP.name)
    return msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="actually send (default is preview only)")
    ap.add_argument("--attach-data", action="store_true", help="attach eastern_drc_flood_data.zip")
    ap.add_argument("--write-page", action="store_true",
                    help="write docs/handover_email.md (intro + letter) for copy-paste, then exit")
    args = ap.parse_args()

    if args.write_page:
        # Generated, not hand-maintained: the intro lives in this script and the
        # body in docs/handover_letter.md, so the page cannot drift from either.
        out = ROOT / "docs" / "handover_email.md"
        parts = [
            "<!-- GENERATED by send_handover_email.py --write-page.",
            "     Do not edit by hand: change the INTRO in that script, or",
            "     docs/handover_letter.md, and re-run. -->",
            "",
            "**Subject:** " + SUBJECT,
            "",
            "**To:** " + ", ".join(TO),
            "",
            "---",
            "",
            INTRO.rstrip(),
            "",
            LETTER_PATH.read_text(encoding="utf-8"),
        ]
        out.write_text("\n".join(parts), encoding="utf-8")
        print("Wrote " + str(out) + f" ({out.stat().st_size:,} bytes)")
        return


    msg = build(args.attach_data)
    attachments = [p.get_filename() for p in msg.iter_attachments()]
    print("=" * 70)
    print(f"From    : {msg['From']}")
    print(f"To      : {msg['To']}")
    if msg["Cc"]: print(f"Cc      : {msg['Cc']}")
    print(f"Subject : {msg['Subject']}")
    print(f"Attached: {', '.join(attachments) or 'none'}")
    print("=" * 70)
    print(msg.get_body(preferencelist=("plain",)).get_content()[:1500])
    print("... [truncated preview] ...\n")

    if not args.send:
        print("Preview only. Nothing sent. Re-run with --send to send it.")
        return

    print(f"This will send to: {', '.join(TO + CC)}")
    if input("Type SEND to confirm: ").strip() != "SEND":
        sys.exit("Cancelled.")

    pw = getpass.getpass(f"Gmail APP PASSWORD for {FROM_ADDRESS} (not your account password): ")
    if not pw.strip():
        sys.exit("No password entered. Cancelled.")

    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        smtp.starttls(context=ctx)
        try:
            smtp.login(FROM_ADDRESS, pw)
        except smtplib.SMTPAuthenticationError:
            sys.exit("Login refused. Gmail requires an App Password with 2-Step "
                     "Verification enabled; the normal account password will not work.")
        smtp.send_message(msg)
    print(f"Sent to {', '.join(TO + CC)}.")


if __name__ == "__main__":
    main()
