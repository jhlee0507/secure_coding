import argparse
import html
import re
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parent.parent


def safe_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "", value).strip()
    if not value:
        raise ValueError("제출자 정보가 비어 있습니다.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="제출용 보안 코딩 보고서 HTML 생성")
    parser.add_argument("--class-name", required=True)
    parser.add_argument("--student-name", required=True)
    parser.add_argument("--phone-suffix", required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"\d{4}", args.phone_suffix):
        raise SystemExit("phone-suffix는 숫자 4자리여야 합니다.")
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", args.repository):
        raise SystemExit("공개 GitHub 저장소 URL을 입력하세요.")

    replacements = {
        "{{STUDENT_NAME}}": html.escape(args.student_name),
        "{{CLASS_NAME}}": html.escape(args.class_name),
        "{{PHONE_SUFFIX}}": args.phone_suffix,
        "{{REPOSITORY_URL}}": html.escape(args.repository),
    }
    source = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    for key, value in replacements.items():
        source = source.replace(key, value)

    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(source)
    css = """
      @page { size: A4; margin: 18mm 16mm 20mm; }
      * { box-sizing: border-box; }
      body { max-width: 980px; margin: auto; color: #17211b; font: 10.5pt/1.65 'Noto Sans CJK KR', 'Noto Sans KR', sans-serif; }
      h1 { font-size: 25pt; border-bottom: 3px solid #176b4d; padding-bottom: 10pt; }
      h2 { color: #176b4d; font-size: 17pt; margin-top: 24pt; break-after: avoid; }
      h3 { font-size: 13pt; break-after: avoid; }
      table { width: 100%; border-collapse: collapse; font-size: 8.7pt; }
      th, td { border: 1px solid #abb8b0; padding: 5pt; vertical-align: top; }
      th { background: #e7f3ed; }
      code { background: #eef1ed; padding: 1pt 3pt; }
      pre { white-space: pre-wrap; background: #f2f4f1; border-left: 4px solid #176b4d; padding: 9pt; }
      a { color: #0d4934; overflow-wrap: anywhere; }
      li { margin-bottom: 2pt; }
      blockquote { border-left: 4px solid #ffca58; margin-left: 0; padding-left: 10pt; }
    """
    document = f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>Secure Coding Report</title><style>{css}</style></head><body>{body}</body></html>"

    class_name = safe_filename(args.class_name)
    student_name = safe_filename(args.student_name)
    filename = f"[WHS][secure-coding][{class_name}]{student_name}({args.phone_suffix}).html"
    output_dir = ROOT / "dist"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / filename
    output.write_text(document, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

