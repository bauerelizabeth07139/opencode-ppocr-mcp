#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP-OCRv6 Medium MCP Server
==========================
MCP (Model Context Protocol) stdio server for PP-OCRv6 Medium OCR.
Uses ONNX Runtime engine for inference.

Tools:
    ocr_image  - Perform OCR on an image file, returns recognized text
    ocr_pdf    - Perform OCR on a PDF file, returns recognized text per page

Usage (opencode config):
    "mcp": {
        "ppocr": {
            "type": "local",
            "command": ["python", "path/to/server.py"]
        }
    }

Requirements:
    pip install paddlepaddle==3.0.0 paddleocr==3.7.0 onnxruntime Pillow
"""

import json
import os
import re
import sys
import traceback

SERVER_NAME = "ppocr-v6m"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18"]

try:
    import msvcrt
except ImportError:
    msvcrt = None


def log(msg):
    try:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()
    except Exception:
        pass


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from paddlex.inference.pipelines import create_pipeline
        log("Loading PP-OCRv6 Medium models...")
        _pipeline = create_pipeline(
            "ocr",
            text_detection_model_name="PP-OCRv6_medium_det",
            text_recognition_model_name="PP-OCRv6_medium_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            engine="onnxruntime",
        )
        log("PP-OCRv6 Medium pipeline loaded.")
    return _pipeline


def handle_tools_list():
    return {
        "tools": [
            {
                "name": "ocr_image",
                "description": (
                    "Perform OCR on an image file using PP-OCRv6 Medium. "
                    "Supports PNG, JPG, JPEG, BMP, TIFF, WEBP formats. "
                    "Returns recognized text with confidence scores and bounding boxes."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Absolute path to the image file.",
                        }
                    },
                    "required": ["image_path"],
                },
            },
            {
                "name": "ocr_pdf",
                "description": (
                    "Perform OCR on a PDF file using PP-OCRv6 Medium. "
                    "Processes each page and returns recognized text per page "
                    "with confidence scores."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "Absolute path to the PDF file.",
                        },
                        "start_page": {
                            "type": "integer",
                            "description": "First page to process (1-based, default 1).",
                            "default": 1,
                        },
                        "end_page": {
                            "type": "integer",
                            "description": "Last page to process (inclusive, default all pages).",
                        },
                    },
                    "required": ["pdf_path"],
                },
            },
        ]
    }


def handle_ocr_image(image_path):
    if not os.path.isfile(image_path):
        return error_content("File not found: %s" % image_path)

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
        return error_content(
            "Unsupported image format '%s'. Supported: PNG, JPG, JPEG, BMP, TIFF, WEBP." % ext
        )

    try:
        pipeline = get_pipeline()
        result = list(pipeline.predict(image_path))
    except Exception as e:
        return error_content("OCR failed: %s\n%s" % (e, traceback.format_exc()))

    if not result:
        return text_content("No text detected.")

    res = result[0]
    rec_texts = res.get("rec_texts", [])
    rec_scores = res.get("rec_scores", [])
    rec_polys = res.get("rec_polys", [])

    if not rec_texts:
        return text_content("No text detected in the image.")

    lines = []
    lines.append("PP-OCRv6 Medium OCR Result")
    lines.append("=" * 40)
    lines.append("File: %s" % os.path.basename(image_path))
    lines.append("Detected %d text region(s)" % len(rec_texts))
    lines.append("")

    combined_text = []
    for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
        box = rec_polys[i] if i < len(rec_polys) else None
        if box is not None:
            bbox = "[%d,%d,%d,%d]" % (
                int(box[:, 0].min()),
                int(box[:, 1].min()),
                int(box[:, 0].max()),
                int(box[:, 1].max()),
            )
        else:
            bbox = ""
        lines.append(
            "  [%d] %s  conf=%.3f  bbox=%s" % (i + 1, text, score, bbox)
        )
        combined_text.append(text)

    lines.append("")
    lines.append("-" * 40)
    lines.append("Combined text:")
    lines.append("\n".join(combined_text))

    return text_content("\n".join(lines))


def handle_ocr_pdf(pdf_path, start_page=1, end_page=None):
    if not os.path.isfile(pdf_path):
        return error_content("File not found: %s" % pdf_path)

    ext = os.path.splitext(pdf_path)[1].lower()
    if ext != ".pdf":
        return error_content("File is not a PDF: %s" % pdf_path)

    try:
        pipeline = get_pipeline()
        result = list(pipeline.predict(pdf_path))
    except Exception as e:
        return error_content("PDF OCR failed: %s\n%s" % (e, traceback.format_exc()))

    if not result:
        return text_content("No text detected in the PDF.")

    lines = []
    lines.append("PP-OCRv6 Medium PDF OCR Result")
    lines.append("=" * 40)
    lines.append("File: %s" % os.path.basename(pdf_path))

    total_pages = len(result)
    lines.append("Total pages: %d" % total_pages)

    if start_page < 1:
        start_page = 1
    if end_page is None or end_page > total_pages:
        end_page = total_pages

    lines.append("Processing pages %d-%d" % (start_page, end_page))
    lines.append("")

    all_text = []
    for page_idx in range(start_page - 1, end_page):
        res = result[page_idx]
        rec_texts = res.get("rec_texts", [])
        rec_scores = res.get("rec_scores", [])

        lines.append("--- Page %d ---" % (page_idx + 1))
        if not rec_texts:
            lines.append("  (no text detected)")
        else:
            for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
                lines.append("  [%d] %s  (%.3f)" % (i + 1, text, score))
            page_text = "\n".join(rec_texts)
            all_text.append(page_text)
        lines.append("")

    lines.append("=" * 40)
    lines.append("All text combined:")
    lines.append("\n".join(all_text))

    return text_content("\n".join(lines))


def handle_tools_call(name, arguments):
    args = arguments or {}
    if name == "ocr_image":
        return handle_ocr_image(str(args.get("image_path", "")))
    elif name == "ocr_pdf":
        return handle_ocr_pdf(
            str(args.get("pdf_path", "")),
            start_page=int(args.get("start_page", 1)),
            end_page=args.get("end_page"),
        )
    return error_content("Unknown tool: %s" % name)


def text_content(text):
    return {"content": [{"type": "text", "text": text}]}


def error_content(message):
    return {
        "content": [{"type": "text", "text": "Error: " + message}],
        "isError": True,
    }


def handle_request(request):
    if request.get("jsonrpc") != "2.0":
        return None
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params") or {}
    is_notification = req_id is None

    def respond(result):
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def respond_error(code, message):
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    if method == "initialize":
        client_proto = params.get("protocolVersion", "")
        proto = client_proto if client_proto in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[-1]
        return respond({
            "protocolVersion": proto,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    elif method == "notifications/initialized":
        return None
    elif method == "notifications/cancelled":
        return None
    elif method == "ping":
        return respond({})
    elif method == "tools/list":
        try:
            return respond(handle_tools_list())
        except Exception as e:
            return respond_error(-32603, str(e))
    elif method == "tools/call":
        try:
            return respond(handle_tools_call(params.get("name"), params.get("arguments")))
        except Exception as e:
            return respond_error(-32603, str(e))
    elif method in ("resources/list", "resources/read", "prompts/list", "prompts/get"):
        return respond(
            {"resources": []} if method == "resources/list"
            else {"prompts": []} if method == "prompts/list"
            else {}
        )
    else:
        return respond_error(-32601, "Method not found: %s" % method)


def main():
    try:
        import io
        out = sys.stdout
        if isinstance(out, io.TextIOWrapper):
            out.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    log("ppocr-v6m MCP server starting (version %s)" % SERVER_VERSION)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError as e:
            log("Ignoring invalid JSON line: %s" % e)
            continue
        response = handle_request(request)
        if response is not None:
            try:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                break


if __name__ == "__main__":
    main()