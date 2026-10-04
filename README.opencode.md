# opencode-ppocr-mcp

PP-OCRv6 Medium MCP Server for OpenCode - 本地 OCR 文字识别工具

## 简介

基于百度 PaddleOCR 的 PP-OCRv6 Medium 模型，通过 ONNX Runtime 进行高效推理，为 OpenCode 提供本地图片和 PDF 的文字识别能力。

- 模型：PP-OCRv6 Medium（检测 + 识别）
- 推理引擎：ONNX Runtime (CPU)
- 协议：MCP Stdio JSON-RPC 2.0

## 安装

### 1. 环境要求

```
Python >= 3.8
pip >= 20.0
```

### 2. 安装依赖

```bash
pip install paddlepaddle==3.0.0 paddleocr==3.7.0 onnxruntime Pillow
```

### 3. 首次运行

首次运行时模型会自动下载至 `~/.paddlex/official_models/` 目录，共约 170MB。

## 配置 OpenCode

在 `opencode.jsonc` 中添加 MCP 配置：

```jsonc
{
  "mcp": {
    "ppocr": {
      "type": "local",
      "command": ["python", "path/to/server.py"],
      "enabled": true
    }
  }
}
```

## 可用工具

### ocr_image

对图片进行 OCR 识别，支持 PNG / JPG / JPEG / BMP / TIFF / WEBP 格式。

参数：
- `image_path` (必填)：图片文件的绝对路径

返回：识别到的文字内容、置信度、边界框坐标。

### ocr_pdf

对 PDF 文件进行 OCR 识别，逐页处理。

参数：
- `pdf_path` (必填)：PDF 文件的绝对路径
- `start_page` (可选)：起始页码，默认为 1
- `end_page` (可选)：结束页码，默认处理所有页面

返回：每页识别到的文字内容。

## 速度参考

CPU 推理（i5-12400F 级别），800x600 图片，10 行文本：

| 耗时 | 说明 |
|------|------|
| ~4s | 首次加载（含模型初始化） |
| ~3s | 单次推理 |

## 注意事项

- 首次运行需联网下载模型文件
- 仅支持 CPU 推理，如需 GPU 加速请安装 `onnxruntime-gpu`
- 如需更快的速度，可将模型名改为 `PP-OCRv6_small_det` + `PP-OCRv6_small_rec`

## 许可证

MIT