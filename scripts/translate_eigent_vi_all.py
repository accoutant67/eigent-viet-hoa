#!/usr/bin/env python3
"""Complete remaining Vietnamese frontend messages using an open-source
English→Vietnamese translation model. Preserve human translations and i18n
placeholders, markup, whitespace, and plural conventions.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "src/i18n/locales"
SOURCE_DIR = LOCALES / "en-us"
DEST_DIR = LOCALES / "vi"
FILES = (
    "agents.json", "chat.json", "common.json", "connectors.json",
    "dashboard.json", "folder.json", "layout.json", "markdown.json",
    "setting.json", "triggers.json", "update.json", "workforce.json",
)
PLURALS = re.compile(r"_(?:zero|one|two|few|many|other)$")
PARAMS = re.compile(r"{{\s*([^},\s]+)(?:\s*,[^}]*)?}}")
TAGS = re.compile(r"</?([A-Za-z0-9][\w-]*)\b[^>]*>")
PROTECTED = re.compile(
    r"({{[^{}]*}}|</?[A-Za-z][^>]*>|https?://[^\s<>]+|"
    r"\x60[^\x60]*\x60|\$\{[^{}]*}|"
    r"\{[a-zA-Z_]\w*}|%\d*\$?[sdf]|\\[nr]|\n)", re.DOTALL
)
TECH = re.compile(r"^(?:[A-Z0-9_.:/@#%+\-=]+|(?:[A-Z]{2,}\s?)+)$")
GLOSSARY = {
    "Eigent": "Eigent", "OpenAI": "OpenAI", "MCP": "MCP",
    "Save": "Lưu", "Cancel": "Hủy", "Delete": "Xóa",
    "Edit": "Chỉnh sửa", "Add": "Thêm", "Settings": "Cài đặt",
    "Account": "Tài khoản", "Agents": "Tác nhân AI", "Agent": "Tác nhân AI",
    "Chat": "Trò chuyện", "Skills": "Kỹ năng", "Tasks": "Tác vụ",
    "Task": "Tác vụ", "Sessions": "Phiên làm việc",
    "Session": "Phiên làm việc", "Close": "Đóng", "Open": "Mở",
    "Search": "Tìm kiếm", "Download": "Tải xuống",
    "Upload": "Tải lên", "Retry": "Thử lại",
    "Continue": "Tiếp tục", "Back": "Quay lại", "Next": "Tiếp theo",
}

def flatten(value, prefix="", result=None):
    if result is None:
        result = {}
    if isinstance(value, dict):
        for key, item in value.items():
            flatten(item, f"{prefix}.{key}" if prefix else key, result)
    else:
        result[prefix] = value
    return result

def nested_set(obj, dotted, value):
    *parents, name = dotted.split(".")
    cur = obj
    for part in parents:
        cur = cur.setdefault(part, {})
    cur[name] = value

def omit_plural(key, source):
    match = PLURALS.search(key)
    return bool(match and match.group() != "_other"
                and key[:match.start()] + "_other" in source)

def signature(value):
    return (
        sorted(PARAMS.findall(value)),
        sorted(("/" if m.group(0).startswith("</") else "") + m.group(1)
               for m in TAGS.finditer(value) if not m.group(0).endswith("/>")),
        re.match(r"^\s*", value).group(),
        re.search(r"\s*$", value).group(),
        sorted(re.findall(r"\{[a-zA-Z_]\w*}", value)),
    )

def valid(original, translated):
    return (isinstance(translated, str) and bool(translated.strip())
            and signature(original) == signature(translated))

def resources():
    for name in FILES:
        en = flatten(json.loads((SOURCE_DIR / name).read_text("utf-8")))
        target = DEST_DIR / name
        vi = flatten(json.loads(target.read_text("utf-8"))) if target.exists() else {}
        yield name, en, vi

def validate(catalogs):
    summary = {"total": 0, "translated": 0, "untranslated": 0}
    problems = []
    for name, en, vi in catalogs:
        expected = {key for key in en if not omit_plural(key, en)}
        for key in sorted(expected - vi.keys()):
            problems.append(f"{name}: missing {key}")
        for key in sorted(vi.keys() - expected):
            problems.append(f"{name}: unexpected {key}")
        for key in sorted(expected & vi.keys()):
            if not valid(en[key], vi[key]):
                problems.append(f"{name}: invalid template {key}")
        summary["total"] += len(expected)
        summary["translated"] += sum(en[k] != vi.get(k) for k in expected if k in vi)
        summary["untranslated"] += sum(en[k] == vi.get(k) for k in expected if k in vi)
    if problems:
        raise RuntimeError("Failed translation contract:\n" + "\n".join(problems[:100]))
    return summary

def split_long(value, max_chars=280):
    while len(value) > max_chars:
        cut = value.rfind(" ", 70, max_chars)
        cut = cut + 1 if cut >= 0 else max_chars
        yield value[:cut]
        value = value[cut:]
    if value:
        yield value

def should_translate(part):
    value = part.strip()
    return bool(
        value and re.search(r"[a-zA-Z]", value)
        and not (
            TECH.fullmatch(value)
            and (
                value in {"AI", "API", "MCP", "GPT", "LLM", "JSON", "XML", "CSV",
                          "PDF", "HTML", "CSS", "SQL", "SSO", "HTTP", "HTTPS",
                          "URL", "SDK", "ID", "CPU", "GPU", "UUID", "JWT"}
                or bool(re.search(r"[0-9_./:@+#%=\\-]", value))
            )
        )
        and not re.fullmatch(r"[\w@/+\-]+(?:[.:/][\w@/+\-]+)+", value)
        and not value.startswith(("data:", "file:", "npm ", "git "))
    )

class Translator:
    def __init__(self, name, batch_size):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        torch.set_num_threads(2)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=False)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(name, trust_remote_code=False)
        self.model.eval()
        self.batch_size = batch_size
        codes = getattr(self.tokenizer, "supported_language_codes", []) or []
        self.prefix = ">>vie<< " if ">>vie<<" in codes else ""

    def translate(self, source):
        result = []
        with self.torch.inference_mode():
            for index in range(0, len(source), self.batch_size):
                chunk = [self.prefix + s for s in source[index:index+self.batch_size]]
                encoded = self.tokenizer(chunk, return_tensors="pt", padding=True,
                                         truncation=True, max_length=400)
                output = self.model.generate(**encoded, num_beams=4, max_new_tokens=384)
                result.extend(self.tokenizer.batch_decode(output, skip_special_tokens=True))
        return result

def translate(catalogs, model, batch_size):
    jobs = []
    fragments = {}
    for name, en, vi in catalogs:
        for key, original in en.items():
            if omit_plural(key, en) or not isinstance(original, str):
                continue
            if vi.get(key) and vi[key] != original:  # Never overwrite human translation.
                continue
            if not any(should_translate(s) for s in PROTECTED.split(original)
                       if s and not PROTECTED.fullmatch(s)):
                continue
            jobs.append((name, key, original))
            for piece in PROTECTED.split(original):
                if not piece or PROTECTED.fullmatch(piece):
                    continue
                for segment in split_long(piece):
                    value = segment.strip()
                    if should_translate(value) and value not in GLOSSARY:
                        fragments[value] = None

    print(f"Entries to translate: {len(jobs)}; distinct segments: {len(fragments)}", flush=True)
    engine = Translator(model, batch_size)
    entries = list(fragments)
    for start in range(0, len(entries), 48):
        chunk = entries[start:start+48]
        for original, translated in zip(chunk, engine.translate(chunk)):
            fragments[original] = translated.strip() or original
        if start % 480 == 0:
            print(f"Translated {min(start+48,len(entries))}/{len(entries)} segments", flush=True)

    replacements = {}
    for name, key, original in jobs:
        result = []
        for part in PROTECTED.split(original):
            if not part:
                continue
            if PROTECTED.fullmatch(part):
                result.append(part)
                continue
            for segment in split_long(part):
                value = segment.strip()
                if not should_translate(value):
                    result.append(segment)
                    continue
                leading = re.match(r"^\s*", segment).group()
                trailing = re.search(r"\s*$", segment).group()
                result.append(leading + GLOSSARY.get(value, fragments.get(value, value)) + trailing)
        translated = "".join(result)
        if not valid(original, translated):
            print(f"WARNING: kept original due to template mismatch: {name}/{key}", flush=True)
            translated = original
        replacements[(name, key)] = translated

    for name, en, vi in catalogs:
        result = {}
        for key, original in en.items():
            if omit_plural(key, en):
                continue
            nested_set(result, key, replacements.get((name, key), vi.get(key, original)))
        (DEST_DIR / name).write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return len(jobs)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true",
                        help="Validate i18n keys and placeholders without model dependencies")
    parser.add_argument("--model", default="Helsinki-NLP/opus-mt-en-vi")
    parser.add_argument("--batch-size", type=int, default=12)
    args = parser.parse_args()
    catalogs = list(resources())
    print("Before:", json.dumps(validate(catalogs), ensure_ascii=False), flush=True)
    if args.check_only:
        return
    changed = translate(catalogs, args.model, args.batch_size)
    print(f"Machine translation attempted on {changed} messages", flush=True)
    print("After:", json.dumps(validate(list(resources())), ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
