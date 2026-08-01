# P2 — MCP Interface Contract Research Findings

**Topic:** MCP (Model Context Protocol) server design patterns and LLM tool interface design — tool granularity, JSON schema design, composition models, LLM prompt engineering for tool use.
**Method:** Tavily search + extract across 10 targeted queries (MCP spec, server examples, tool-use best practices, video-editing JSON schemas, FFmpeg APIs, prompt engineering).
**Date:** 2026-07-21

---

## 1. MCP Specification — Tool Definitions & JSON Schema Format

### Pattern: JSON-RPC 2.0 Tool Discovery + Call
The MCP spec (modelcontextprotocol.io, spec version 2025-03-26 and later drafts) defines exactly two RPC endpoints a tool server must implement:

- **`tools/list`** — client requests available tools; server returns an array of tool definitions.
- **`tools/call`** — client invokes a tool by name with a JSON arguments object; server returns a result payload.

### Tool Definition Shape
Every tool has, at minimum:

```json
{
  "name": "get_dns_records",
  "description": "Retrieve DNS records for a zone",
  "inputSchema": {
    "type": "object",
    "properties": {
      "zone_id": { "type": "string", "description": "The zone ID (e.g., example-zone-123)" },
      "record_type": {
        "type": "string",
        "enum": ["A", "AAAA", "CNAME", "MX", "TXT"],
        "description": "DNS record type"
      }
    },
    "required": ["zone_id", "record_type"]
  }
}
```

### JSON Schema Dialect Rules (from the spec)
- **Default dialect: JSON Schema 2020-12** when `$schema` is absent.
- Schemas MAY declare `$schema` for a different dialect; implementations MUST support at least 2020-12.
- The full protocol is defined as a **TypeScript schema** (source of truth), with JSON Schema auto-generated from it.
- `_meta` is a reserved property for protocol-level metadata (prefixed key names like `modelcontextprotocol.io/foo`).

### Tool Result Content Types
A `tools/call` result contains a `content` array of typed blocks:
- `{ "type": "text", "text": "..." }`
- `{ "type": "resource", "resource": { "uri": "...", "mimeType": "...", "text": "..." } }`
- (image/audio blocks also exist in the spec.)

### Key Takeaway for Our Design
The schema is the LLM's *only* contract. MCP deliberately flattens parameters into a single JSON object (no path/query/header split like REST) because "AI engines struggle to track these distinct contexts" (aakanksha blog). For an FFmpeg MCP, every operation should be a self-contained JSON object with all context in parameters.

---

## 2. MCP Server Examples — How Existing Servers Structure Tools

### Filesystem / GitHub / Memory (official reference servers)
Configured via `claude_desktop_config.json` as stdio processes (`npx -y @modelcontextprotocol/server-filesystem /path/to/allowed/files`). Key patterns:
- **Filesystem server**: fine-grained tools (`read_file`, `write_file`, `list_directory`, `create_directory`, `move_file`, `search_files`...) — one operation per tool.
- **GitHub server**: ~26 fine-grained tools mirroring the GitHub REST API surface (`create_or_update_file`, `search_repositories`, `create_pull_request`...).
- Official servers use **snake_case verb-noun** names consistently.

### Slack MCP servers (3 community implementations studied)
- **ubie-oss/slack-mcp-server**: Zod-schema-first pattern — "1. Define request/response using Zod schemas (Request schema: input params; Response schema: responses limited to necessary fields). 2. Validate request → call Slack WebAPI → parse response to limit to necessary fields → return JSON." Tools: `slack_list_channels`, `slack_post_message`, `slack_reply_to_thread`, `slack_add_reaction`, `slack_get_channel_history`, `slack_get_thread_replies`, `slack_get_users`, `slack_search_messages`.
- **korotovsky/slack-mcp-server**: feature-gated tools via env vars (`SLACK_MCP_REACTION_TOOL` enables `reactions_add`/`reactions_remove`; can whitelist channel IDs). Pattern: **dangerous tools are opt-in and scope-restrictable**.
- **bitovi/slack-mcp-server**: per-tool file layout (`internal/tools/read_message.go`, `list_channel_messages.go`, `search_messages.go`) with per-tool tests. Example tool schema:

```json
{
  "name": "list_channel_messages",
  "inputSchema": {
    "type": "object",
    "properties": {
      "channel_id": { "type": "string", "description": "Slack channel ID (e.g., C01234567)" },
      "limit": { "type": "number", "description": "Number of messages to retrieve (default: 100, max: 200)" },
      "oldest": { "type": "string", "description": "Only return messages after this Unix timestamp" },
      "latest": { "type": "string", "description": "Only return messages before this Unix timestamp" }
    },
    "required": ["channel_id"]
  }
}
```

Note the description style: **every parameter has an example value and constraints inline** (`default: 100, max: 200`).

### FastMCP 2.0 (Python) pattern
```python
from fastmcp import FastMCP
mcp = FastMCP("Minesweeper Pro")

@mcp.tool
def new_game(difficulty: str = "beginner") -> dict:
    """Start a new Minesweeper game!"""
    ...

@mcp.resource("game://state/{game_id}")
def get_game_state(game_id: str) -> str: ...

@mcp.prompt
def strategy_guide(situation: str) -> str: ...
```
Three primitives: **Tools** (model-controlled actions), **Resources** (app-controlled read-only data), **Prompts** (reusable prompt templates). The Minesweeper example is a **stateful composition model**: `new_game` returns a `game_id`, and subsequent calls (`reveal`, `get_hint`) take `game_id` — state externalized into a handle the LLM carries.

---

## 3. LLM Tool-Use Best Practices — Granularity, Parameter Design, Errors

### Pattern: Scenario-Oriented Descriptions (meta-intelligence synthesis of research)
Four core schema elements: `name`, `description`, `parameters`, `required`.
- `name`: snake_case, verb-first (`get_weather`, `create_ticket`).
- `description` is **the most critical field** — model tool selection relies primarily on its semantics. Should be *scenario-oriented* not *function-oriented*: "Use this tool when a user asks about product prices, inventory, or product details" beats "Query the product database."

### Six Principles of Parameter Design (from the same source + AWS blog)
1. **Enum constraints for discrete values** — `"enum": ["value1", "value2"]` prevents invalid values and shrinks the model's decision space.
2. **Examples in descriptions** — `"Search keywords, such as 'wireless Bluetooth headphones'"` clarifies semantic boundaries.
3. **Distinguish required vs optional** — sensible defaults let the model call effectively with partial info.
4. **Rename params to match the LLM's domain model, not your DB columns** — `resource_class` with values like "Student Resource" beats `content_bucket` (AWS).
5. **Set defaults to the most common values** so the LLM only specifies what varies (AWS).
6. **Keep parameter counts ~8 or fewer** (AWS Prescriptive Guidance for MCP). Drop fields the LLM can't use well.

### Pattern: Consistent Naming Across a Toolkit (Brenndoerfer)
"If some functions use `user_id` and others use `userId` or `uid`, the model struggles." Consistent naming reduces cognitive overhead and makes parameter extraction more reliable. Keep required params minimal — "every required parameter is a point of potential failure."

### Error Handling Patterns

#### MCP's two error channels (official spec, server/tools):
1. **Protocol errors** — standard JSON-RPC errors for unknown tools, invalid arguments, server errors:
```json
{ "jsonrpc": "2.0", "id": 1, "error": { "code": -32602, "message": "Invalid params" } }
```
Standard codes: `-32700` parse error, `-32600` invalid request, `-32601` method not found, `-32602` invalid params, `-32001` unauthorized/insufficient scope (with `data` carrying `granted_scopes`/`required_scope`).

2. **Tool execution errors** — returned as **successful JSON-RPC responses with `isError: true`**, NOT protocol errors (per MCP spec 2025-06-18, confirmed by the ash_ai issue fix):
```json
{
  "jsonrpc": "2.0", "id": 2,
  "result": {
    "content": [{ "type": "text", "text": "The requested travel date cannot be set in the past. You requested travel on July 31st, 2024, but the current date is July 25th, 2025. Did you mean July 31st, 2025?" }],
    "isError": true
  }
}
```
Rationale (Alpic): "Tool-call error responses are context, not dead ends" — the LLM sees the error and self-corrects next turn. Protocol errors are invisible/dead-end to the model.

#### Error message style guide (levelup.gitconnected — "every MCP tool response is a prompt"):
- **Required**: `isError: true` on every failure; single text block, one short sentence containing (1) what failed, (2) which parameter/system caused it, (3) whether/how to retry. Reference params by exact schema name in backticks.
- **Forbidden**: raw HTTP status codes, stack traces, "Request failed", `isError: false` wrapping an error message (model treats it as success).
- Example of a good error: "The `start_date` parameter is required but was not provided. Pass it in ISO-8601 format (e.g. `2026-01-15`)."

#### Agent-level error loops (agenticai-flow):
- **Pre-validation with Pydantic/Zod** before tool execution; feed ValidationError back to LLM with specific instructions ("input argument format is incorrect") — "dramatically increases the probability the LLM generates corrected JSON in the next turn."
- **Categorize tools by risk**: Read-only (retry aggressively, exponential backoff) / Computation (validate inputs+outputs, sandbox) / Actions that mutate external state (design idempotent; retries dangerous).
- Structural errors (broken JSON, missing args) vs Runtime errors (rate limits, API down) need different handling.

### Tool Granularity Research
- **"Less is More" (arXiv 2411.15399)**: dynamically reducing the tool set improves accuracy and speed — three search levels: individual tools → clustered tool groups → whole set as fallback. Presenting fewer tools reduces LLM confusion.
- **Anthropic Tool Search Tool**: up to **85% token reduction** by loading tool definitions only when relevant (cited in AWS blog).
- **Granite Function Calling (arXiv 2407.00121)**: multi-task learning over granular sub-tasks (function name detection, parameter extraction, sequencing) improves calling accuracy; +8% F1 on name detection vs. next best.

### AWS MCP Tool Design — six evolutionary versions (very relevant)
AWS's blog documents iterating one tool through 6 designs:
1. **V1 minimal schema** — LLM guesses wrong enum values ("quiz" vs "Assessment"); silent empty results cause retry churn. "Low baseline cost is misleading when confusion drives up actual cost."
2. **V2 rich descriptions** — valid values documented inline.
3. **Schema constraints** — enums in the schema itself.
4. **Response shaping** — return 5 decision-relevant fields by default, detailed view on demand; cut response tokens ~2/3.
5. **Restructuring + on-demand context** — split multi-purpose tools into specific ones; lazy-loading discovery tool.
6. **V6 Agent-as-tool** — one external tool `agentic_search_content(question: str)` backed by an internal agent with its own system prompt and hidden internal tools. The external interface is one tool, one parameter; internal complexity invisible to the client LLM.

---

## 4. JSON Schemas for Video Editing — Timelines & Composition Models

### Shotstack Edit JSON (the dominant cloud video-editing API model)
```json
{
  "timeline": {
    "tracks": [
      {
        "clips": [
          {
            "asset": { "type": "image", "src": "https://..." },
            "start": 0,
            "length": 3,
            "effect": { "type": "zoomIn" }
          },
          {
            "asset": { "type": "video", "src": "https://..." },
            "start": 3,
            "length": 10,
            "transition": { "in": { "type": "fade" } }
          },
          {
            "asset": { "type": "title", "text": "This is a video editing API", "style": "minimal" },
            "start": 13,
            "length": 5
          }
        ]
      }
    ]
  },
  "output": { "format": "mp4", "resolution": "sd" }
}
```
**Model:** Timeline → Tracks (layering, z-order) → Clips (asset + start + length + transition/effect). Asset types: image, video, title, audio, html, luma. Submit via POST → async render → poll status. Response: `{ "success": true, "message": "Created", "response": { "id": "d2b46ed6-..." } }`.

### JSON2Video / Creatomate
Same declarative model: scenes, text, images, audio, transitions in clean JSON; template + placeholder variables for personalization at scale.

### OpenTimelineIO (OTIO) — the industry interchange schema (Academy Software Foundation)
JSON-serialized object graph; every object carries `"OTIO_SCHEMA": "TypeName.version"` for independent schema versioning. Canonical structure:

```
Timeline.1 → tracks: Stack.1 → children: [Track.1, Track.1, ...]
Track.1 → children: [Clip.1 | Gap.1 | Transition.1 | Composition.1]
Clip.1 → media_reference: ExternalReference.1 { target_url, available_range: TimeRange }
       + source_range (trim within available_range), effects, markers, metadata
RationalTime.1 → { "rate": 24, "value": 10 }   ← frame-accurate time as rational numbers
Transition.1 → { "transition_type": "SMPTE_Dissolve", "in_offset", "out_offset" }
```

Key OTIO concepts worth borrowing:
- **`available_range` vs `source_range`** — full media extent vs. the trimmed segment actually used. Maps directly to FFmpeg's `-ss`/`-t` on inputs.
- **Stack vs Track** — vertical composition (Stack) vs horizontal sequence (Track). Nested `Composition` objects for reusable sub-sequences.
- **Frame-accurate rational time** (`rate`/`value`) instead of float seconds — avoids float drift in edits.
- **`MissingReference`** — represent unavailable media explicitly with metadata, rather than failing.
- Metadata dictionary on every object for blind data.

### IMG.LY mobile timeline design
Same mental model confirmed: "A digital video composition consists of tracks for simultaneous audio and video layers. These tracks contain individual clips that can be rearranged, trimmed, and transformed."

### Stack Overflow web-editor data model
`TimeLine → VideoGroup/AudioGroup → Track → Media` — group layer between timeline and tracks to separate audio/video track semantics.

---

## 5. FFmpeg Automation APIs — Existing Wrappers

### ClipChat Engine (saranshhardaha/clipchat) — MOST RELEVANT to our project
Open-source video-editing backend: **natural language → FFmpeg via REST API + MCP server**.
- Exposes **20 FFmpeg operations as tools**, dual interface: REST (async BullMQ job queue + SSE progress) and MCP server (stdio, `--mcp` flag, synchronous direct FFmpeg).
- Architecture: Express API (`/files`, `/jobs`, `/tools`, `/chat`) → BullMQ worker → FFmpeg subprocess → PostgreSQL result. Chat flow: LLM call streams tool calls → jobs queued → poll until done (max 60s) → second LLM call synthesizes results.
- **MCP flow: AI agent calls tool → FFmpeg runs synchronously → result returned immediately.**
- Also has `GET /api/v1/tools` tool manifest and `POST /api/v1/tools/:name` direct invocation.

### Video Editor MCP (Kush36Agrawal) — single-tool anti-pattern example
Python MCP server with **one main tool: `execute_ffmpeg`** — natural-language requests like "Crop video.mp4 from 1:30 to 2:45" are interpreted by the LLM into FFmpeg args. This is the maximal-flexibility/minimal-safety endpoint of the granularity spectrum. Includes progress tracking and error handling. (~49 stars on GitHub; related: Vedit-MCP, vidmagik-mcp which wraps MoviePy.)

### OpenCut MCP (emerged mid-July 2026)
Dedicated video-editor MCP where "the agent interprets instructions, plans the timeline, and calls the appropriate MCP tools (`splice_track`, `add_overlay`, `render_video`) **in sequence**." Example of **timeline-oriented tool naming** (not FFmpeg-command-oriented) — tools map to editing concepts, not CLI flags.

### FFmpeg Micro (ffmpeg-micro.com) — commercial FFmpeg REST + MCP
REST API: submit transcode job → poll → download. MCP server for Claude Code/Desktop/Cursor. Philosophy: "submit a job, poll until it finishes, download the result" — **async job model**, agent handles polling.

### Rendi — raw FFmpeg command API
Exposes raw FFmpeg command lines over REST (max control, max risk). Positioned vs. Shotstack (templated JSON) as the two ends of the abstraction spectrum.

### IMG.LY FastAPI batch processor (reference architecture)
Docker-based: `VideoProcessor` (executes FFmpeg tasks) + `JobQueue` (worker pool, concurrent execution) + `ConfigManager` (**processing profiles and workflows** = named, reusable parameter sets). Endpoints for jobs, profiles, workflows, uploads. Pattern: **profiles/workflows as first-class resources** so common operations are consistent and discoverable.

### samisalkosuo/ffmpeg-api — simple endpoint-per-operation REST
`POST /convert/video/to/mp4`, `POST /video/extract/audio`, `POST /video/extract/images` — URL-path-encoded operations, file in request body, converted file in response. Simplest possible mapping.

---

## 6. LLM Prompt Engineering for Tool Calling

### Few-Shot Prompting for Tool Calls (LangChain, July 2024)
- Few-shot prompting (example model inputs + desired outputs in the prompt) "greatly boosts model performance" on tool calling.
- Multiverse Math experiment: tools that behave differently from standard operations (2×3 = f(2,3)) force genuine tool reliance. Key failure mode found: **LLM calls the tool correctly but ignores the output** and answers from internal knowledge — only fixed by explicitly prompting the model to respect tool output.
- Technique: extract real conversation trajectories (messages after the system prompt) and use them as few-shot examples.
- Multi-call agentic setups produce `trajectories of multiple LLM calls` — evaluation must be trajectory-level, not single-call.

### Chain-of-Thought + Tool Use
- CoT (step-by-step reasoning) combines with few-shot for complex multi-step tool tasks. Zero-shot CoT ("Let's think step by step") for simple cases.
- **ReACT prompting** (Yao et al. 2022) — interleaved Thought/Action/Observation — remains the reference framework for tool-using agents (cited in Granite paper).
- ToolLLM/DFSDT: depth-first-search decision trees for multi-tool tasks over 16,000+ real APIs (ToolBench).

### Anthropic "Building Effective Agents" (the canonical agent-design doc)
- **Workflows vs Agents**: workflows = LLMs+tools orchestrated through predefined code paths (predictable); agents = LLMs dynamically direct their own process and tool usage. "Consistently, the most successful implementations use simple, composable patterns rather than complex frameworks."
- Five workflow patterns: **Prompt Chaining, Routing, Parallelization, Orchestrator-Workers, Evaluator-Optimizer.**
- Orchestrator-workers is "the golden pattern" for complex tasks with unpredictable subtasks (e.g., multi-file coding) — one LLM coordinates, workers execute.
- Thought-Action-Observation cycle is the orchestration glue.
- Antipatterns to avoid: monolithic agents, over-engineered planning, missing observability (every reasoning step and tool interaction must be traceable in production).

---

## 7. MCP Composition Models — Stateful vs Stateless

### The core tradeoff (Medium/bhavyshekhaliya, Dysnix, MCP Discussion #102, SEP-2575)
- **Stateless**: every request self-contained; easy load balancing/scaling; but the client (and the LLM!) must carry all context — e.g., passing auth tokens and handles in every call.
- **Stateful**: server remembers session (session ID header, initialization handshake); supports multi-phase workflows, sampling, progress notifications; but breaks behind standard load balancers without sticky sessions.
- **Hybrid (the production consensus)**: tool calls themselves stateless; server keeps a lightweight session layer only for infrastructure plumbing (auth tokens, connection pools) — "the session doesn't hold business logic state."

### SEP-2575 "Make MCP Stateless" + the 2026 spec direction
The protocol is moving to **stateless-by-default at the transport layer** (no handshake, no session header). State moves to the application layer via **explicit handles**: "the model can see the handle, compose it across tools, and hand it off between steps — in ways that session state hidden in transport metadata never allowed." Redis/backing stores hold what handles point to. **"Stateless protocol, stateful application."**

### Three state patterns (Zeo architecture blog)
1. **Server-Side State Cache** — stateful facade for agent interactions over stateless backend microservices.
2. **State Externalization via signed resource URIs** — server returns short-lived "pointers" representing stateful data; client includes them in subsequent requests. Trades infra complexity for security complexity.
3. **Hybrid control plane/resource plane** — MCP server (control plane) manages app state; backend services stateless.

### Minesweeper/ClipChat handle pattern
`new_game()` → returns `game_id`; `reveal(game_id, x, y)`; `get_hint(game_id)`. The handle IS the composition mechanism: the LLM chains tools by passing handles. This is exactly how a video project/timeline handle should work in our design (`create_project` → `project_id` → `add_clip(project_id, ...)` → `render(project_id)`).

---

## 8. MCP Tool Naming & Description Standards

### Naming (Snyk, AWS DESIGN_GUIDELINES, zazencodes survey of 100 servers, SEP-986)
- Allowed charset: `^[a-zA-Z0-9_-]{1,64}$` — no spaces, dots, or brackets (breaks MCP client discovery).
- **snake_case recommended** (`read_file`, `create_entities`); kebab-case and PascalCase accepted. **Pick one style per server, never mix.**
- Verb-noun pattern: `get_status`, `create_user`. Begin with imperative verb (`get_`, `list_`, `create_`).
- ≤32 chars ideal; fully-qualified name (with server prefix) must stay under 64 chars.
- GPT-4o tokenization works best with snake_case/camelCase; dots and spaces fragment tokenization and tools silently don't get called.
- Prefix-based category naming (ShotGrid MCP): `prefix_action_qualifier`.

### Descriptions (arXiv 2602.14878 "Tool Descriptions Are Smelly", awesome-mcp-best-practices)
- Study scanned 856 real MCP tools with an LLM jury against a rubric from Anthropic's design guidelines + 15 practitioner sources — poor descriptions are endemic.
- Avoid: "Call this function to execute an SQL query" (function-oriented, no scenario).
- Prefer: when-to-use scenarios, capability boundaries, return format, aliases ("if the user says X, this tool handles it").
- **Tool naming aliases**: call out alternate phrasings in the description so the LLM invokes `postMessage` when user says "share a social post."
- Pagination matters: return "showing N of total, use offset X for next page" so the agent can page (MCP Server Design Best Practices video).

---

## 9. Synthesis — Design Recommendations for the FFmpeg MCP Project

| Decision | Evidence-backed recommendation |
|---|---|
| **Granularity** | Mid-granularity: editing-concept tools (`trim_clip`, `merge_videos`, `add_overlay`) not raw `execute_ffmpeg` (unsafe, the Kush36Agrawal single-tool model) and not 1:1 FFmpeg-flag wrappers. Keep ≤~20 tools (ClipChat's count; "Less is More" granularity research). |
| **Composition** | Handle-based state externalization: `create_project → project_id` threaded through calls, matching SEP-2575's stateless-protocol/stateful-application direction and the Minesweeper/ClipChat handle pattern. |
| **Timeline schema** | Shotstack-style JSON (Timeline → Tracks → Clips with start/length/transition) as the composition document; adopt OTIO's `source_range`/`available_range` distinction for trim semantics and rational time if frame accuracy matters. |
| **Schema style** | JSON Schema 2020-12; enums for all discrete params; examples+constraints in every param description; ≤8 params per tool (AWS guidance); consistent snake_case verb-noun names. |
| **Async model** | Two-tier: short ops synchronous (ClipChat MCP flow); long renders async with job handle + progress (FFmpeg Micro / BullMQ pattern). `isError: true` + one-sentence actionable errors everywhere. |
| **Errors** | Never JSON-RPC errors for execution failures; `isError: true` with (what failed, which param, how to retry) in one sentence. Pre-validate with Zod/Pydantic and feed validation errors back verbatim. |
| **Prompt layer** | Ship `@mcp.prompt` templates for common workflows (trim-and-caption, social-clip extraction) + few-shot trajectory examples in the system prompt; explicitly instruct the model to respect tool outputs (LangChain Multiverse Math lesson). |

---

## GAPS REQUIRING PERPLEXITY DEEP RESEARCH

1. **Concrete FFmpeg MCP tool schemas in the wild** — ClipChat's README lists "20 tools" and dual REST/MCP flow, but the actual per-tool JSON schemas (parameter names, types, descriptions) were not extractable via Tavily. Need deep-dive into the repo's tool manifest (`GET /api/v1/tools`) and `packages/` source, plus OpenCut MCP's actual `splice_track`/`add_overlay`/`render_video` schemas.
2. **MCP outputSchema / structured tool results** — The 2025-06-18+ spec added `outputSchema` for tools and structured content in results. Tavily results did not surface the exact spec text, migration status, or client support matrix (which hosts honor structured output vs. text-only).
3. **Sampling (server-initiated LLM calls) real implementations** — Referenced repeatedly as the reason to keep stateful connections, but no working code examples of an MCP server using `sampling/createMessage` for e.g. auto-generating captions mid-render were found.
4. **Progress notifications spec details** — `notifications/progress` is mentioned in the stateful/stateless debate, but the exact message format, client display behavior, and how LLMs (not just UIs) consume progress for long FFmpeg renders is undocumented in search results.
5. **Token-cost measurements per granularity level** — The 85% (Tool Search Tool) and 2/3 (AWS response shaping) figures are cited secondhand; no primary benchmarks comparing e.g. 5 coarse vs 20 fine tools for a fixed video-editing task suite. MCP-Universe benchmark exists (231 tasks, 202 tools) but its per-domain results aren't in Tavily's reach.
6. **FFmpeg filter-graph composition as JSON** — No project found that exposes FFmpeg's filter_complex DAG as a declarative JSON graph (nodes/edges) for LLM composition. Whether anyone has designed a validated JSON Schema for filter graphs (vs. flat clip timelines) is an open question.
7. **OTIO→FFmpeg render pipelines** — OTIO is an interchange format; no evidence found of a maintained, production OTIO→FFmpeg renderer (only OTIO↔NLE adapters). Whether to adopt OTIO natively or only borrow its semantics needs deeper investigation (otio-ffmpeg adapter status, Remotion's composition JSON schema details).
8. **LLM retry/correction behavior on `isError: true` at scale** — Practitioner consensus (Alpic, levelup) is strong, but no measured data on how many correction turns different error-message styles cost across Claude/GPT/Gemini.
9. **MCP Elicitation (server requesting user input mid-tool)** — The 2025-era spec addition for interactive clarification wasn't surfaced at all; could matter for "which of these 3 clips did you mean?" flows.
10. **Versioning strategies for MCP tool schemas** — How production servers evolve tool schemas without breaking pinned clients (deprecation headers, `v2_` tool names, capability negotiation at initialize) found no treatment beyond OTIO's `"OTIO_SCHEMA": "Type.version"` pattern.
