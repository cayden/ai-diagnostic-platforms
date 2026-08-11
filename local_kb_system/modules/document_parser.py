# -*- coding: utf-8 -*-
"""湖企智库 - 文档解析：PDF / Word / Excel / PPT / TXT / MD / CSV
优先使用专用库，缺失时回退到 zipfile/标准库弱解析，保证开箱即用。"""
import os
import re
import zipfile
import xml.etree.ElementTree as ET


def _read_plain(path):
    for enc in ("utf-8", "gbk", "gb18030", "utf-16"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, "r", errors="ignore") as f:
        return f.read()


def _docx_text(path):
    """docx = zip + word/document.xml"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    # 保留段落边界，剔除标签
    xml = xml.replace("</w:p>", "\n")
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _xlsx_text(path):
    """xlsx = zip; 提取 sharedStrings + sheet XML 中的文本"""
    texts = []
    try:
        with zipfile.ZipFile(path) as z:
            shared = []
            if "xl/sharedStrings.xml" in z.namelist():
                root = ET.fromstring(z.read("xl/sharedStrings.xml"))
                ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                for si in root.findall("a:si", ns):
                    txt = "".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
                    shared.append(txt)
            sheets = [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)]
            for sn in sheets[:3]:
                root = ET.fromstring(z.read(sn))
                ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                row_vals = []
                for row in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                    vals = []
                    for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                        v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                        t = c.get("t")
                        if v is None or v.text is None:
                            continue
                        if t == "s":
                            try:
                                vals.append(shared[int(v.text)])
                            except (IndexError, ValueError):
                                pass
                        else:
                            vals.append(v.text)
                    if vals:
                        row_vals.append(" | ".join(vals))
                texts.append("\n".join(row_vals))
    except Exception:
        return ""
    return "\n".join(texts)


def _pptx_text(path):
    texts = []
    try:
        with zipfile.ZipFile(path) as z:
            slides = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml", n)],
                            key=lambda n: int(re.search(r"\d+", n).group()))
            for sn in slides[:20]:
                xml = z.read(sn).decode("utf-8", "ignore")
                xml = xml.replace("</a:p>", "\n")
                txt = re.sub(r"<[^>]+>", "", xml)
                if txt.strip():
                    texts.append(txt.strip())
    except Exception:
        return ""
    return "\n".join(texts)


def parse_document(path):
    """返回纯文本内容；不支持的格式返回 ''"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".txt", ".md", ".csv"):
            return _read_plain(path)
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                return "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception:
                return _read_plain(path)  # 弱回退
        if ext == ".docx":
            return _docx_text(path)
        if ext == ".doc":
            # 老格式无法用标准库解析
            return ""
        if ext in (".xlsx",):
            return _xlsx_text(path)
        if ext == ".xls":
            return ""
        if ext == ".pptx":
            return _pptx_text(path)
        if ext == ".ppt":
            return ""
    except Exception as e:
        return f""
    return ""
