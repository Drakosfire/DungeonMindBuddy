Mastering Tiptap’s AI Toolkit for DungeonBuddy

Overview

The Tiptap editor is a ProseMirror‑based toolkit that lets you build rich‑text editors. The AI Toolkit is a commercial extension that augments Tiptap with document‑aware AI agents and AI‑driven workflows. It provides a collection of tools and workflows that allow large language models (LLMs) to read, understand and manipulate documents precisely. This report explains the key concepts, APIs and best practices you need to build expert agents for DungeonBuddy.

Core ideas: AI agents vs. workflows

Tiptap distinguishes between AI agents and workflows:

Agents are given a goal (e.g., rewrite a paragraph) and decide which tool calls to make. Tool calls are executed with executeTool. This is ideal for chat‑based assistants that need reasoning and autonomy.
Workflows perform a fixed sequence of operations (e.g., insert content, proofread). They don’t decide what tools to call; you provide the content and task, and the workflow streams the changes back to the editor. Workflows are simpler to implement and require smaller models.

The AI Toolkit works with any LLM that supports function‑calling. It provides tool definitions for popular AI libraries (Vercel AI SDK, LangChain.js, OpenAI, Anthropic and others). The model can call tools like tiptapRead or tiptapEdit, and you apply them with executeTool.

Reading the document

Before an AI model can edit, it needs context. The read tools extract content from the editor in various formats and split large documents into chunks to stay within token limits:

Tool	Purpose (short)	Key details
getTextRange	Read plain text from a range	Takes {from, to} and returns a string.
getHtmlRange	Read HTML from a range	Same as getTextRange but returns HTML.
getMarkdownRange	Read Markdown	Requires the Markdown extension and returns Markdown for the range.
getJsonRange	Read ProseMirror JSON	Returns JSON content for the specified range.
getTextChunks, getHtmlChunks, getJsonChunks	Split content into 32k‑character chunks	Useful for large documents; each chunk includes its content and the range it covers.
tiptapRead, tiptapReadChunks	Read the document in a special “Tiptap Read” format optimized for editing	tiptapRead returns a single string; tiptapReadChunks splits it into chunks.
tiptapReadSelection	Read currently selected content	Returns the selected content and its range so the AI knows what to edit.

These reading tools prevent the model from ingesting the entire document at once. The chunkSize option limits how many characters each call can send to the AI.

Editing the document

The AI Toolkit exposes several writing tools. They insert or stream content into the document and accept an optional position (number or range) and reviewOptions to control how changes are presented:

insertText(content, options) – Inserts plain text. If position is a range, it replaces that range; if a number, it inserts at that index.
insertHtml(content, options) – Inserts HTML content.
insertJson(content, options) – Inserts ProseMirror JSON nodes or slices.
streamText(stream, options) – Streams text from an async iterator into the editor. Allows real‑time updates and includes callbacks to detect errors in chunks.
streamHtml(stream, options) – Streams HTML content.

For agents, the tiptapEdit tool performs complex operations (replace, insert before, insert after) using an array of operations. You call it via executeTool with an operations list. This is used by workflows like Tiptap Edit.

Review options

Every editing method accepts reviewOptions to let users review AI‑generated changes. Modes include:

disabled – Apply changes directly.
review – Apply changes and show a review UI for undoing them.
preview – Show a preview before applying changes so users can accept/reject.
trackedChanges – Encode changes as tracked changes using the Tracked Changes extension; users can accept or reject each change.

reviewOptions also accepts metadata and display options to customize how suggestions appear.

Tool definitions and execution

An agent receives tool definitions (metadata describing each tool) via the AI provider library. When the model calls a tool, your code executes it using executeTool:

const toolkit = getAiToolkit(editor);
const result = await toolkit.executeTool({
  toolName: 'tiptapRead',
  input: { from: 0 },
});

The AI Toolkit’s tool definitions currently include at least tiptapRead, tiptapEdit, tiptapReadSelection and getThreads. Each defines input types and results. For example, tiptapRead reads content from a position; tiptapEdit applies operations; tiptapReadSelection returns selected text.

Selection awareness and schema awareness
Selection awareness

The tiptapReadSelection tool allows the AI agent to see exactly what is selected. It returns the content and range of the selection. To prevent user‑induced selection changes from confusing the AI, you can set an active selection before the AI runs and unset it afterward using setActiveSelection. Models with reasoning enabled tend to respect the selection better.

Schema awareness

A Tiptap schema defines what nodes and marks (paragraphs, headings, tables, custom nodes, etc.) are allowed. Without schema awareness, an AI might generate unsupported elements (e.g., tables in a document that disallows tables). Tiptap’s getHtmlSchemaAwareness method returns a string describing the editor’s schema that you should append to the AI’s system prompt. You can add descriptions for custom nodes via the addHtmlSchemaAwareness option, and then include the schema awareness string in your API request; this helps the model generate valid content.

Suggestions and review workflows

After AI edits, suggestions are shown so users can decide which changes to accept. A Suggestion contains an id, a range, replacement options (text or ProseMirror slices), optional display attributes and metadata. Key methods in the suggestions API:

getSuggestions() – Return all active suggestions.
getSelectedSuggestion() – Return the suggestion at the cursor.
setSuggestions(suggestions) / addSuggestions(suggestions) – Replace or append suggestions.
setSuggestionsFromDiff({ doc, reviewOptions }) – Compare the current document with another document and create suggestions automatically.
acceptSuggestion(id, options) / rejectSuggestion(id) – Accept or reject individual suggestions and receive feedback events.
acceptAllSuggestions(options) / rejectAllSuggestions(options) – Accept or reject all suggestions at once.
setMarkdownSuggestions({ content | changes, range, reviewOptions }) – Generate suggestions by comparing corrected Markdown with the document. Supports full document or individual text replacements.
invertSuggestions() – Apply all current suggestions to a copy of the document and return inverted suggestions that undo those changes.

Suggestions rely on the diff utility when previewing edits. The diffUtility function compares two documents and returns changes. It supports smart, inline (character‑level) and block diff modes and options like simplifyChanges and changeMergeDistance. You can start and stop real‑time comparisons with startComparingDocuments and stopComparingDocuments.

Built‑in AI workflows

Tiptap’s AI Toolkit includes ready‑made workflows that simplify building common features. They combine tiptapRead and tiptapEdit calls with streaming and suggestions. Each workflow has a server function (to call your model) and a client function (to apply operations/suggestions). Key workflows:

Proofreader – Detects and fixes grammar and spelling mistakes. Use createProofreaderWorkflow on the server and proofreaderWorkflow on the client. You stream suggestions and allow users to accept all or reject all.
Tiptap Edit – General‑purpose workflow for editing content. It supports replacing content, inserting before/after nodes and is triggered with a task (e.g., “Make the text more formal”). Use createTiptapEditWorkflow on the server and tiptapEditWorkflow on the client.
Insert content – (not fully accessible) A simpler workflow for inserting new content at a selected location; it restricts editing to a specific range and is ideal when the AI must insert new paragraphs or images.
Comments – Manages threads and comments. The AI can create threads, add comments, update or remove comments, and mark them resolved. The workflow uses the Comments extension and editThreadsWorkflow on the client.
Template – Allows the AI to fill variables in a template document. You send the document content and variable values; the workflow inserts the variables into the appropriate places.
Best practices for AI engineering

The AI engineering guide offers recommendations on choosing models, prompts and optimizing performance:

Model selection: Use frontier models with tool‑calling for complex agentic tasks (GPT‑5, Claude Opus, Gemini Pro, Mistral Large, etc.). Budget models like GPT‑5 mini or Claude Haiku work for simpler tasks. The toolkit works with any model that supports function‑calling.
Reasoning: Enabling reasoning improves accuracy but increases cost and latency. Set a low reasoning level unless your agent requires step‑by‑step planning.
Prompt engineering: Supply a clear system prompt that describes the assistant’s role. Include the schema awareness string and refer to tool names when instructing the model. You don’t need to list tool definitions—the model receives them automatically.
Streaming: For responsiveness, stream AI responses and apply them incrementally. Implement streaming both server‑side (with streamText) and client‑side using the AI SDK’s streaming utilities.
Latency: Choose providers or models optimized for speed and consider disabling reasoning to reduce latency.
Applying to DungeonBuddy

DungeonBuddy currently uses a command board for AI actions. To add editable text and formatting:

Integrate Tiptap Editor. Use @tiptap/react with @tiptap/starter-kit to initialize an editor. Use AiToolkit extension to enable AI capabilities.
Set up AI access: Connect your LLM provider (OpenAI, Anthropic, etc.). Use the tool definitions from @tiptap-pro/ai-toolkit-tool-definitions so the model knows how to call Tiptap tools. If building a workflow, import createProofreaderWorkflow, createTiptapEditWorkflow or other workflow functions.
Provide schema awareness and selection awareness: On each edit, call getHtmlSchemaAwareness() and append it to your system prompt to ensure the AI respects your document schema. Use setActiveSelection to fix the selection before sending a command if you want the AI to edit only a specific range.
Reading and writing: Use tiptapRead or tiptapReadSelection to send the relevant context to the AI. When the AI returns tool calls (in agentic mode) or operations (in workflows), call executeTool or the appropriate workflow method to apply changes.
Review and suggestions: Decide whether to allow users to preview AI changes. Use reviewOptions to display suggestions or tracked changes. Provide UI controls for accepting or rejecting suggestions (acceptAllSuggestions, rejectSuggestion, etc.).
Manage comments and metadata: If your documents need comments, integrate the Comments extension and use the Comments workflow to let the AI annotate passages. This is valuable for feedback on adventure narratives or rules interpretations.
Conclusion

The Tiptap AI Toolkit offers a powerful foundation for building AI‑assisted rich‑text editing in DungeonBuddy. By understanding the reading and writing tools, selection and schema awareness features, suggestion APIs, diff utilities and workflows, you can build agents that perform precise, context‑aware edits while still giving users control. Careful model choice, prompt design and streaming will ensure the integration is both responsive and trustworthy.