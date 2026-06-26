"""
PDF 文本解析工具模块

支持从 PDF 附件中提取文本内容，用于补充招标公告的资质要求、评分办法等字段。
"""

import io
import logging
import re
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# 尝试导入 PDF 解析库
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF (fitz) 未安装，PDF解析功能受限。请执行: pip install PyMuPDF")

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def extract_text_from_pdf_bytes(
    pdf_bytes: bytes,
    max_pages: int = 20,
) -> str:
    """
    从 PDF 文件的二进制内容中提取纯文本。

    优先使用 PyMuPDF（fitz），回退到 pdfplumber。

    Args:
        pdf_bytes: PDF 文件的二进制数据
        max_pages: 最大解析页数（防止超大文件）

    Returns:
        提取的文本内容。解析失败返回空字符串。
    """
    if not pdf_bytes:
        return ""

    # ── 方案1: PyMuPDF ──
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            texts = []
            for page_num in range(min(len(doc), max_pages)):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    texts.append(text)
            doc.close()
            result = "\n".join(texts)
            logger.info(f"PDF解析(PyMuPDF): {len(doc)}页, {len(result)}字符")
            return result
        except Exception as e:
            logger.warning(f"PyMuPDF解析失败: {e}")

    # ── 方案2: pdfplumber ──
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texts = []
                for page in pdf.pages[:max_pages]:
                    text = page.extract_text()
                    if text:
                        texts.append(text)
                result = "\n".join(texts)
                logger.info(f"PDF解析(pdfplumber): {len(pdf.pages)}页, {len(result)}字符")
                return result
        except Exception as e:
            logger.warning(f"pdfplumber解析失败: {e}")

    # ── 方案3: 原始字节流（最后手段） ──
    try:
        text = pdf_bytes.decode("utf-8", errors="ignore")
        # 过滤明显的二进制垃圾
        text = re.sub(r"[^\x20-\x7e\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\n\r]", " ", text)
        if len(text) > 100:
            logger.info(f"PDF解析(raw): {len(text)}字符")
            return text
    except Exception:
        pass

    logger.error("PDF解析完全失败")
    return ""


def extract_fields_from_pdf_text(pdf_text: str) -> Dict:
    """
    从 PDF 提取的文本中识别关键字段。

    Returns:
        {
            "budget": float|None,
            "qualification": str,
            "score_weight": dict|None,
            "contact_info": str,
        }
    """
    if not pdf_text:
        return {"budget": None, "qualification": "", "score_weight": None, "contact_info": ""}

    result = {
        "budget": _extract_budget_from_text(pdf_text),
        "qualification": _extract_qualification_from_text(pdf_text),
        "score_weight": _extract_score_from_text(pdf_text),
        "contact_info": _extract_contact_from_text(pdf_text),
    }
    return result


def _extract_budget_from_text(text: str) -> Optional[float]:
    """从文本提取预算金额（万元）。"""
    patterns = [
        r"(?:预算|采购预算|项目预算|预算金额|控制价)[：:是为]?\s*[¥￥]?\s*(\d[\d,.]*)\s*万",
        r"(?:预算|采购预算|项目预算|预算金额|控制价)[：:是为]?\s*[¥￥]?\s*(\d{4,})\s*元",
        r"(\d+\.?\d*)\s*万元",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = float(m.group(1).replace(",", ""))
            if "元" in m.group(0) and "万" not in m.group(0):
                val = val / 10000
            return round(val, 2)
    return None


def _extract_qualification_from_text(text: str) -> str:
    """从文本提取资格要求段落。"""
    patterns = [
        r"(?:投标人|供应商|申请人|应答人).{0,10}(?:资格|资质).{0,5}(?:要求|条件)[：:]?\s*(.{50,1000}?)(?=\n\s*(?:[一二三四五六七八九十]、|\d+[.、]|（[一二三四五六七八九十]）|$)|\Z)",
        r"(?:资格|资质)(?:要求|条件|审查).{0,5}[：:]?\s*(.{50,1000}?)(?=\n\s*(?:[一二三四五六七八九十]、|\d+[.、])|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            result = m.group(1).strip()[:2000]
            if len(result) >= 20:
                return result

    # 回退: 包含"资格"的段落
    idx = text.find("资格")
    if idx >= 0:
        start = max(0, idx - 20)
        end = min(len(text), idx + 300)
        snippet = text[start:end].strip()
        if len(snippet) > 20:
            return snippet

    return ""


def _extract_score_from_text(text: str) -> Optional[Dict[str, float]]:
    """从文本提取评分权重。"""
    tech_m = re.search(r"技术(?:分|部分|权重)?[：:占]?\s*(\d+)\s*(?:%|分)", text)
    biz_m = re.search(r"商务(?:分|部分|权重)?[：:占]?\s*(\d+)\s*(?:%|分)", text)
    price_m = re.search(r"价格(?:分|部分|权重)?[：:占]?\s*(\d+)\s*(?:%|分)", text)

    if tech_m or biz_m or price_m:
        return {
            "tech": float(tech_m.group(1)) / 100 if tech_m else 0,
            "biz": float(biz_m.group(1)) / 100 if biz_m else 0,
            "price": float(price_m.group(1)) / 100 if price_m else 0,
        }
    return None


def _extract_contact_from_text(text: str) -> str:
    """提取联系方式。"""
    patterns = [
        r"(?:联系人|联系电话|联系方式)[：:]\s*(.{10,200}?)(?:\n|$)",
        r"(?:采购人|招标人).{0,10}(?:地址|联系人|电话)[：:]\s*(.{10,200}?)(?:\n|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


def download_and_parse_pdf(url: str, session=None) -> Optional[str]:
    """
    下载远程 PDF 并提取文本。

    Args:
        url: PDF 文件的 URL
        session: 可选的 httpx.Client 或 requests.Session

    Returns:
        提取的文本内容，失败返回 None
    """
    import httpx
    try:
        if session:
            resp = session.get(url, timeout=30)
        else:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
        if resp.status_code == 200:
            content = resp.content
            if content[:4] == b"%PDF":
                return extract_text_from_pdf_bytes(content)
            logger.warning(f"非PDF文件: {url[:100]}")
        else:
            logger.warning(f"PDF下载失败 HTTP {resp.status_code}: {url[:100]}")
    except Exception as e:
        logger.error(f"PDF下载异常: {url[:100]} - {e}")
    return None
