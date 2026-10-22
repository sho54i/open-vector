# Vector Assistant and browser tools

Open **Help → Vector Assistant** for connection guidance, or **Help → Agent tools** for the API reference and schema download. The assistant is also available in **Tools → Vector Assistant**. Existing model settings, preview and panel layout migrate automatically; the legacy `__ENTITY_VECTOR__` test API remains available.

## Model connection

Use a local or hosted Chat Completions-compatible API. Supply its HTTP(S) API base, model ID and optional bearer key. Connect discovers models with `GET /models`. Generate uses `POST /chat/completions`; a manually entered model ID bypasses discovery. Requests use standard model/messages/stream/temperature/max_tokens fields with no engine-specific extensions. Services using other protocols need a compatible adapter. Browser CORS and HTTPS restrictions still apply. Nothing is requested automatically at startup.

The model receives the prompt and SVG-format instructions, not the current document. Results go into a separate preview. Insert adds editable copies on the active artboard with one Undo step. Endpoint, model, prompt and accepted preview persist locally; API keys remain in memory only. Cancel and failed generation preserve previous artwork. The existing SVG subset is unchanged: flat-colour basic shapes and M/L/H/V/C/Q/Z paths, 512 shapes and 10,000 anchors maximum. Simplify transforms, arcs, gradients and text before using assistant import.

## Browser agent integration (API version 1)

This is a browser tool API, **not an MCP server or transport**. A browser-capable agent can use it through page evaluation, including a browser MCP tool that evaluates JavaScript. It works on local files and hosted editor pages. Call it in the editor's frame, not an unrelated parent tab. It does not open a network listener or accept cross-origin messages.

```javascript
const api = window.__VECTOR_ASSISTANT__;
api.version; // 1
api.listTools(); // names, descriptions and inputSchema
await api.callTool('get_document', {});
```

`callTool` always resolves to `{ok:true, result}` or `{ok:false, error:{code,message}}`. Arguments are validated; unknown tool names and fields fail. Read operations return detached serializable data. Tools never expose the model key or automatically send document contents to a model.

### End-to-end example with Playwright

Use your existing `page` attached to the open editor:

```python
async def call(name, arguments=None):
    response = await page.evaluate(
        '([name,args]) => window.__VECTOR_ASSISTANT__.callTool(name,args)',
        [name, arguments or {}])
    if not response['ok']:
        raise RuntimeError(response['error'])
    return response['result']

# Inspect without changing the user's document.
document = await call('get_document')
preview = await call('preview_svg', {
    'svg': '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="30" fill="#ffb800"/></svg>'
})
# Review preview['svg'] / browser preview before inserting.
import uuid
insert = await call('insert_preview', {
    'previewId': preview['previewId'],
    'documentRevision': document['documentRevision'],
    'requestId': str(uuid.uuid4())
})
print(insert['pathIds'])
```

### Tools

- `get_document {}` — current outline JSON, selected path IDs and documentRevision. Includes hidden/locked artwork so an agent can understand the full document.
- `get_preview {}` — accepted SVG, path count, previewId, ready/busy state and status; source edits make ready false.
- `preview_svg {svg}` — validates SVG, replaces only the assistant preview, returns its ID and normalized source. Busy model generation is rejected.
- `insert_preview {previewId, documentRevision, requestId}` — inserts independent copies into the active artboard; returns inserted path IDs/count and the new document revision. Refuses changed preview/document, unpreviewed source and active canvas gestures or imports. Never modifies existing paths, including locked/hidden artwork.
- `export_svg {}` — returns document SVG using the editor's current export-area setting; no download and no document change.
- `get_help {}` — returns this guide as Markdown.

Read revisions again after edits, Undo/Redo, artboard changes or reload. Tokens are scoped to this page session. Preview replacement invalidates its token. Camera/selection changes alone do not invalidate the document token. The same requestId with the same arguments returns its successful insertion result instead of inserting twice; changing arguments for a used ID fails. The last 64 successful requests are retained in memory, not across reload. Use a fresh UUID for each intended insertion, and never retry an old insertion after a reload. Undo remains available through the editor's Edit menu/keyboard; the API deliberately exposes only additive document writes.

### Error codes

`UNKNOWN_TOOL`, `INVALID_ARGUMENT`, `BUSY`, `STALE_PREVIEW`, `STALE_DOCUMENT`, `REQUEST_CONFLICT`, `INVALID_SVG`, `NOT_READY`, or `OPERATION_FAILED`. Failures preserve document contents. A stale result means re-read and review the current state; do not silently insert against a different document.

## Verification

`python3 tests/vector_assistant.py` checks real browser calls, compatible model request fixtures, preview isolation, geometry insertion, idempotency, stale tokens, malformed arguments/SVG, source edits, busy guards, history/reload, secret omission, layout migration and keyboard-accessible Help. `python3 tests/entity_panel.py --offline` covers existing preview/clipboard/error/cancel behavior. A live third-party model round trip is not covered by fixture tests.
