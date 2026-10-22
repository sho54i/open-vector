> Updated 2026-10-22: this panel is now **Vector Assistant**. Current connection, browser-agent API and Help documentation: [Vector Assistant](vector-assistant.md). The original implementation notes below are retained for history.

# Entity Harness vector panel

The resident panel lives at the top of the editor's right scrollable inspector.

1. Open `vector_pen_tool.html` and expand **Model connection**.
2. **Connect** detects the loaded model. The default API base is `http://127.0.0.1:8081/v1`, the local model server used by Entity Harness. Another compatible API base and model can be entered. Optional API keys stay in memory and are not saved.
3. Describe the artwork and choose **Generate**. The result appears in the panel preview; the document remains unchanged. Unsupported model output receives one simplification retry. Cancel and a three-minute timeout stop waiting without changing the preview.
4. **Copy** copies the normalized preview SVG. **Paste** reads SVG into the preview; if clipboard access is unavailable, paste into **Vector source / manual paste** and choose **Preview source**.
5. **Insert** centers the artwork on the artboard, adds editable paths in front, selects them and zooms to them. One Undo removes the insertion. Subsequent insertion creates a fresh independent copy.

Connection, model, prompt and accepted preview are remembered in browser local storage. Source edits must be previewed before they can be inserted. No automatic model requests occur on page load.

## SVG scope

Flat-color paths (`M L H V C Q Z`), rectangles, circles, ellipses, lines, polylines and polygons. Basic inherited fill/stroke on groups is supported. Unsupported features such as text, transforms, arcs, gradients, clipping and compound filled paths report an error instead of silently changing the artwork. The preview is generated from validated editable geometry and displayed as an image; model-supplied DOM/scripts are never mounted. Artwork is centered and scaled down if larger than the artboard. Generated SVG coordinates are rounded to three decimals by the existing exporter.

## Connection investigation, 2026-09-06

- `GET http://127.0.0.1:8002/llama/v1/models` succeeds and exposes `fable-agentic-0.8b`.
- Generation through that proxy fails with HTTP 502: `llama proxy error: Too much data for declared Content-Length`.
- In `AiM/Entity/entity cli/memory_server.py`, the proxy can inject context into the request body but forwards the original Content-Length header. That separate service was not modified as part of this editor change.
- Direct generation at `http://127.0.0.1:8081/v1/chat/completions` works, including browser CORS access, so this is the panel default.
- The loaded 0.8B model can produce unsupported, repetitive or compositionally poor SVG. The panel validates output and can retry format errors once; visual quality still depends on the selected model and prompt.

## Verification

Run from DRAW with Python Playwright and Chromium installed:

```
python3 tests/entity_panel.py           # real local-model round trip + interaction tests
python3 tests/entity_panel.py --offline # deterministic SVG / failure fixtures, no model generation
python3 tests/precision.py
python3 tests/snapping.py
python3 tests/rulers.py
```

The panel regression checks preview isolation, rendered gold/cyan pixels, insertion/undo/redo, clipboard controls with a browser clipboard fixture, manual fallback, malformed/unsupported SVG, HTTP errors, cancellation and local-storage restore. Live mode additionally verifies the real model response and saves a sample SVG and screenshot. The real generation check validates the vector flow, not artistic fidelity to the prompt.

The preview work also fixed a pre-existing `pathToD` export defect: Y values incorrectly subtracted the X origin. X and Y offsets are now applied independently, preventing cropped previews and SVG exports.
