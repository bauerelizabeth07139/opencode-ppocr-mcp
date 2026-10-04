# opencode-ppocr-mcp

**Local OCR, no cloud.** PP-OCRv6 Medium detection + recognition on ONNX
Runtime (CPU), for images and multi-page PDFs.

*本地 OCR:PP-OCRv6 Medium 检测+识别,ONNX Runtime CPU 推理,可识别图片与多页 PDF。*

As a DeepSeek Harness plugin: the MCP server ships inside the bundle, so
installing one plugin is the whole setup — no `mcpServers` file to hand-edit.

## Install

**DeepSeek Harness Desktop** — open **Plugins** in the sidebar, choose **Add
plugin**, and enter:

```
https://github.com/bauerelizabeth07139/opencode-ppocr-mcp
```

Then switch the new **dsh-ppocr** bundle on. The Desktop app boots the
reserved `desktop` profile, so that is where it has to be enabled.

**dsh CLI** — install it into the profile you actually boot:

```sh
dsh plugin --profile web add bauerelizabeth07139/opencode-ppocr-mcp
```

**No git on the machine?** pnpm resolves a git shorthand with `git ls-remote`,
which fails with `'git' is not recognized` when git is missing. Use the tarball
instead — that path is plain HTTPS:

```sh
dsh plugin --profile web add https://codeload.github.com/bauerelizabeth07139/opencode-ppocr-mcp/tar.gz/main
```

The same address works in the Desktop **Add plugin** dialog. Replace `main`
with a commit SHA to pin an exact revision (`/tar.gz/<sha>`).

Uninstall with `dsh plugin --profile web remove dsh-ppocr`.

## Requirements

- **Python ≥ 3.8** on `PATH`, or pointed at with `python`.
- **The OCR stack in that interpreter** — this is the heavy part:

  ```sh
  pip install paddlepaddle==3.0.0 paddleocr==3.7.0 onnxruntime Pillow
  ```

  `requirements.txt` in this repository pins exactly those.
- **Disk and network for the first run:** the detection and recognition models
  (~170 MB) download into `~/.paddlex/official_models/` the first time a tool is
  called. CPU only; no GPU and no display.

## Tools

The server registers `2` tool(s). DSH namespaces them automatically,
so the model calls them as `mcp__ppocr__<tool>`:

| Tool | What it does |
|---|---|
| `ocr_image` | Runs detection + recognition on one image and returns the text. Parameter: `image_path` (required). |
| `ocr_pdf` | Renders and recognises a PDF page by page. Parameters: `pdf_path` (required), `start_page` (default 1), `end_page` (optional). |

## Configuration

| Key | Environment variable | Default | Meaning |
|---|---|---|---|
| `python` | — | discovered | interpreter that runs the server — **must** have the OCR stack |
| `toolCallTimeoutMs` | — | `600000` | DSH's per-call budget; the first call also downloads the models |
| `env` | — | `{}` | raw environment passthrough (the server reads none) |

Every field is optional and lives in the loader row. For example, in
`cordis.patch.yml`:

```yaml
- id: dsh-ppocr
  name: 'dsh-ppocr'
  config:
    python: 'C:\ocr-venv\Scripts\python.exe'
    toolCallTimeoutMs: 900000
```

## Notes

- **The plugin mounts; the interpreter must carry the stack.** The server
  imports PaddleOCR lazily, when a tool is called, so a missing dependency shows
  up as a tool error naming the import rather than a plugin that refuses to
  load. Point `python` at an interpreter that has
  `paddlepaddle`, `paddleocr`, `onnxruntime` and `Pillow`.
- **The first call is slow.** Detection and recognition models (~170 MB)
  download into `~/.paddlex/official_models/` on first use; the 600 s per-call
  budget covers it.
- **`end_page` must be a number.** The server does not coerce it, so passing a
  string makes its comparison fail — pass an integer.

## How it is mounted

`index.js` resolves a Python interpreter (the configured `python`, then
`python3`/`python` on `PATH`), hands the server its argv and working directory,
and mounts it as a stdio MCP server through `@deepseek-ai/dsh-mcp-client` with
`failOnStartupError: true`, so a server that cannot start is a visible error
rather than a silently missing tool.

Credentials are forwarded explicitly. The harness scrubs credential-shaped
variables (`KEY`, `TOKEN`, `SECRET`, `PASSWORD`) out of the environment a child
process inherits, so `config.apiKey` — falling back to the variable the server
documents — is written into the child's environment by the plugin itself. That
means both of these work:

```yaml
config:
  apiKey: '<your key>'
```

```sh
export the API key variable='<your key>'   # picked up at load time
```

## Development

No build step and no runtime dependencies — `@deepseek-ai/cordis` and
`@deepseek-ai/dsh-mcp-client` are peers supplied by the Harness.

```sh
npm test    # node >= 22: manifest checks + the stdio mount, both Harness-free
```

The mount test loads `index.js` with `@deepseek-ai/dsh-mcp-client` stubbed and
asserts the exact stdio configuration the plugin produces, including the
credential forwarding above.

## Repository layout

| Path | Purpose |
|---|---|
| `index.js` | the DSH plugin: resolves the interpreter and mounts the server |
| `cordis.patch.yml` | the loader row that activates the plugin |
| `locale/{en,zh}.json` | card title and description for the plugin lists |
| `assets/icon.svg` | card artwork |
| `test/` | `npm test`: manifest composition and the mount contract |
| `server.py` | the MCP server, unchanged |
| `requirements.txt` | the OCR stack, pinned |

## Other hosts (unchanged)

The server is a plain stdio MCP server and still works anywhere else. The
repository's original README is kept verbatim as
[`README.opencode.md`](README.opencode.md), and the launch stanza from it keeps
working:

```json
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

## License

[MIT](LICENSE) — the repository's README declared MIT but shipped no licence file; this plugin's release adds one.
