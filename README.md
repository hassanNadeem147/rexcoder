# Rexcoder

Rexcoder is a local-first AI coding assistant that helps developers reason about problems, generate code, explain concepts, debug issues, and review implementation quality through a guided workflow.

Built with FastAPI, LangGraph, and Groq, Rexcoder combines conversational AI with a structured multi-step coding pipeline to turn a user request into a practical result.

## Why Rexcoder

Modern coding assistants are powerful, but many workflows feel opaque or too generic. Rexcoder is designed to feel more like a structured engineering partner:

- It classifies the request as a question, generation task, bug fix, or modification request.
- It routes work through specialized pipeline stages such as planning, coding, testing, and final response generation.
- It keeps conversation history in a local SQLite checkpoint store.
- It streams progress in real time to a lightweight web interface.
- It is local-first and workspace-oriented, making it suitable for experimentation and iterative development.

## Features

- Intent-aware planning and routing
- Concept explanations and general coding guidance
- New code generation from a prompt
- Modification and feature implementation support
- Bug investigation and repair planning
- Static review and validation feedback
- Local thread history and persistent context
- Real-time progress streaming via Server-Sent Events
- Browser-based chat interface with lightweight front-end UI

## Tech Stack

- Python 3.10+
- FastAPI for the API layer
- LangGraph for orchestration and stateful workflows
- Groq LLM integration for model inference
- SQLite for checkpoint persistence
- Vanilla JavaScript + HTML + CSS for the frontend

## Architecture Overview

Rexcoder uses a graph-based workflow that routes each user request through a sequence of nodes:

1. Planner: identifies the task type and decides the appropriate flow.
2. Explainer: handles conceptual and explanatory requests.
3. Coder: generates or updates code.
4. Bug Fixer: diagnoses and repairs issues when debugging is required.
5. Tester: reviews generated or modified code for correctness and completeness.
6. Final Response Builder: assembles the final answer for the user.

This structure helps maintain clarity, modularity, and traceability throughout the process.

## Project Structure

```text
Rexcoder/
├── app/
│   ├── api/
│   │   ├── router.py
│   │   └── routes/
│   │       ├── threads_route.py
│   │       └── user_query_route.py
│   ├── core/
│   │   └── config.py
│   ├── graph/
│   │   ├── nodes/
│   │   │   ├── bug_fixer.py
│   │   │   ├── coder.py
│   │   │   ├── explainer.py
│   │   │   ├── final_response_builder.py
│   │   │   ├── planner.py
│   │   │   └── tester.py
│   │   ├── state.py
│   │   └── workflow.py
│   ├── schemas/
│   │   ├── coder_scheme.py
│   │   ├── planner_scheme.py
│   │   ├── tester_scheme.py
│   │   └── user_query_scheme.py
│   └── main.py
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── requirements.txt
├── checkpoints.sqlite
└── README.md
```

## Getting Started

### 1) Prerequisites

- Python 3.10 or newer
- A Groq API key
- A working terminal environment

### 2) Clone the repository

```bash
git clone <your-repository-url>
cd Rexcoder
```

### 3) Create environment variables

Create a `.env` file in the project root with the required values:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

> You can update the model name to any Groq-supported model you prefer.

### 4) Install dependencies

```bash
pip install -r requirements.txt
```

### 5) Run the application

```bash
uvicorn app.main:app --reload
```

The application will start locally, and the frontend will be served from the project root.

Open the app in your browser at:

```text
http://localhost:8000
```

## API Overview

### Streaming user request

```http
POST /api/stream
```

Sends a user message and streams workflow progress as server-sent events. The response includes:

- progress updates from each workflow node
- token-level explanation output
- final generated answer
- optional code snippets
- testing or validation status

### List conversations

```http
GET /api/threads
```

Returns the list of saved thread IDs and titles.

### Fetch one conversation

```http
GET /api/threads/{thread_id}
```

Returns the message history for a specific thread.

## Example Use Cases

- “Explain how Python decorators work with a simple example.”
- “Create a Python function that validates an email address.”
- “Help me find and fix a bug in this code.”
- “Refactor this service to make it more testable and maintainable.”

## Workflow Behavior

The system is intentionally structured around task intent:

- Questions are answered directly with explanations and examples.
- Generated tasks create or draft implementation.
- Debug tasks route into diagnosis and repair flows.
- Modification tasks update or extend existing code with verification in mind.

This makes Rexcoder more reliable for real coding workflows than a single generic chat agent.

## Notes

- Conversation state is stored locally in the SQLite checkpoint database.
- The app is designed for local development and experimentation.
- The system relies on Groq as the inference backend and uses structured prompts to guide behavior.

## Future Improvements

Potential enhancements for the project include:

- richer project-level code context and file-aware prompting
- more advanced automated test execution
- adding repository-aware code reading and patching workflows
- improved conversation summaries and memory management
- authentication and multi-user support for hosted deployments

## Summary

Rexcoder is a practical, local-first AI coding assistant designed to help with explanation, implementation, debugging, and structured review in a single workflow-driven interface. It bridges conversational AI with engineering-oriented task routing, making it a strong foundation for future coding-agent capabilities.
