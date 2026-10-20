const elements = {
  sidebar: document.querySelector("#sidebar"),
  scrim: document.querySelector("#sidebar-scrim"),
  threadList: document.querySelector("#thread-list"),
  newThread: document.querySelector("#new-thread"),
  welcome: document.querySelector("#welcome"),
  messageList: document.querySelector("#message-list"),
  title: document.querySelector("#context-title"),
  form: document.querySelector("#composer"),
  input: document.querySelector("#message-input"),
  send: document.querySelector("#send-button"),
  connectionStatus: document.querySelector("#connection-status"),
};

const API_AVAILABLE = window.location.protocol !== "file:";
let currentThreadId = null;
let activeController = null;

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function inlineMarkdown(value) {
  let text = escapeHtml(value);
  const code = [];
  text = text.replace(/`([^`]+)`/g, (_, contents) => {
    code.push(`<code>${contents}</code>`);
    return `\u0000${code.length - 1}\u0000`;
  });
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  text = text.replace(/\u0000(\d+)\u0000/g, (_, index) => code[Number(index)]);
  return text;
}

function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const output = [];
  let paragraph = [];
  let listType = null;
  let inCode = false;
  let codeLines = [];
  let codeLanguage = "";
  let tableRows = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      output.push(`<p>${paragraph.map(inlineMarkdown).join("<br>")}</p>`);
      paragraph = [];
    }
  };
  const flushList = () => {
    if (listType) {
      output.push(`</${listType}>`);
      listType = null;
    }
  };
  const flushTable = () => {
    if (!tableRows.length) return;
    const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
    const rows = tableRows.filter((row) => !/^\s*\|?\s*:?-{3,}/.test(row));
    if (rows.length) {
      const head = cells(rows[0]);
      output.push("<table><thead><tr>" + head.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join("") + "</tr></thead><tbody>");
      for (const row of rows.slice(1)) {
        output.push("<tr>" + cells(row).map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join("") + "</tr>");
      }
      output.push("</tbody></table>");
    }
    tableRows = [];
  };

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      flushParagraph();
      flushList();
      flushTable();
      if (inCode) {
        output.push(`<pre><code${codeLanguage ? ` class="language-${escapeHtml(codeLanguage)}"` : ""}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        inCode = false;
        codeLines = [];
        codeLanguage = "";
      } else {
        inCode = true;
        codeLanguage = line.trim().slice(3).trim().split(/\s+/)[0] || "";
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }
    if (/^\s*\|.*\|\s*$/.test(line)) {
      flushParagraph();
      flushList();
      tableRows.push(line);
      continue;
    }
    flushTable();
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) {
      flushParagraph();
      flushList();
      output.push("<hr>");
      continue;
    }
    const listItem = line.match(/^\s*(?:[-*+]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      flushParagraph();
      const type = /^\s*\d/.test(line) ? "ol" : "ul";
      if (listType !== type) {
        flushList();
        listType = type;
        output.push(`<${type}>`);
      }
      output.push(`<li>${inlineMarkdown(listItem[1])}</li>`);
      continue;
    }
    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      flushList();
      output.push(`<blockquote>${inlineMarkdown(quote[1])}</blockquote>`);
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();
  flushTable();
  if (inCode) output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  return output.join("");
}

function closeSidebar() {
  elements.sidebar.classList.remove("open");
  elements.scrim.classList.remove("visible");
}

async function resetConversation() {
  if (activeController) activeController.abort();
  activeController = null;
  elements.send.disabled = false;
  currentThreadId = null;
  elements.title.textContent = "New conversation";
  elements.messageList.replaceChildren();
  elements.messageList.classList.remove("visible");
  elements.welcome.hidden = false;
  elements.input.value = "";
  closeSidebar();
  await refreshThreads().catch(renderThreadError);
}

function addMessage(role, content = "", streaming = false) {
  elements.welcome.hidden = true;
  elements.messageList.classList.add("visible");
  const message = document.createElement("article");
  message.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "assistant" ? "R" : "Y";
  const body = document.createElement("div");
  body.className = "message-body";
  const label = document.createElement("div");
  label.className = "message-role";
  label.textContent = role === "assistant" ? "REXCODER" : "YOU";
  const contentElement = document.createElement("div");
  contentElement.className = "message-content";
  contentElement.textContent = content;
  if (streaming) contentElement.classList.add("stream-cursor");
  body.append(label, contentElement);
  message.append(avatar, body);
  elements.messageList.append(message);
  message.scrollIntoView({ block: "end", behavior: "smooth" });
  return contentElement;
}

function renderThreadList(threads) {
  elements.threadList.replaceChildren();
  if (!threads.length) {
    const empty = document.createElement("div");
    empty.className = "thread-empty";
    empty.textContent = "Your conversations will appear here.";
    elements.threadList.append(empty);
    return;
  }
  for (const thread of threads) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `thread-item${thread.thread_id === currentThreadId ? " active" : ""}`;
    button.title = thread.title;
    button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M20 11.5a7.5 7.5 0 0 1-8 7.5 8.7 8.7 0 0 1-3.7-.8L4 20l1.3-3.5A7.1 7.1 0 0 1 4 12c0-4.1 3.6-7.5 8-7.5s8 3.1 8 7Z"/></svg>';
    const title = document.createElement("span");
    title.className = "thread-title";
    title.textContent = thread.title;
    button.append(title);
    button.addEventListener("click", () => openThread(thread.thread_id));
    elements.threadList.append(button);
  }
}

function renderThreadError() {
  elements.threadList.replaceChildren();
  const error = document.createElement("div");
  error.className = "thread-empty";
  error.textContent = "Could not load saved conversations.";
  elements.threadList.append(error);
}

async function refreshThreads() {
  if (!API_AVAILABLE) {
    throw new Error("Open the server URL shown by Uvicorn to use saved conversations.");
  }
  const response = await fetch("/api/threads");
  if (!response.ok) throw new Error("Could not load conversations.");
  const data = await response.json();
  renderThreadList(data.threads);
  return data.threads;
}

async function openThread(threadId) {
  if (activeController) activeController.abort();
  currentThreadId = threadId;
  closeSidebar();
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}`);
  if (!response.ok) {
    showError("This conversation could not be loaded.");
    return;
  }
  const thread = await response.json();
  if (currentThreadId !== threadId) return;
  elements.messageList.replaceChildren();
  elements.messageList.classList.remove("visible");
  elements.welcome.hidden = thread.messages.length > 0;
  for (const message of thread.messages) {
    const content = addMessage(message.role, message.content);
    if (message.role === "assistant") content.innerHTML = renderMarkdown(message.content);
  }
  elements.title.textContent = thread.messages.find((message) => message.role === "user")?.content.slice(0, 70) || "Conversation";
  await refreshThreads().catch(renderThreadError);
}

function showError(message) {
  const notice = document.createElement("div");
  notice.className = "thread-empty";
  notice.setAttribute("role", "alert");
  notice.textContent = message;
  elements.messageList.append(notice);
}

function parseSseEvent(raw) {
  let event = "message";
  const data = [];
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) };
  } catch {
    return null;
  }
}

async function sendMessage(text) {
  if (activeController) return;
  if (!API_AVAILABLE) {
    showError("This page was opened from disk. Start the backend and open the server URL shown by Uvicorn to chat.");
    return;
  }
  const message = text.trim();
  if (!message) return;
  addMessage("user", message);
  elements.input.value = "";
  elements.input.style.height = "auto";
  const answer = addMessage("assistant", "", true);
  const progress = document.createElement("div");
  progress.className = "progress-line";
  progress.innerHTML = '<span class="status-dot"></span><span>Starting workflow...</span>';
  elements.messageList.append(progress);
  const controller = new AbortController();
  activeController = controller;
  elements.send.disabled = true;
  let answerText = "";

  const handleEvent = async (item) => {
    if (!item) return;
    if (item.event === "meta") {
      currentThreadId = item.data.thread_id;
      await refreshThreads().catch(renderThreadError);
    } else if (item.event === "progress") {
      progress.lastElementChild.textContent = item.data.message;
    } else if (item.event === "token") {
      answerText += item.data.text;
      answer.textContent = answerText;
      answer.classList.add("stream-cursor");
      answer.scrollIntoView({ block: "end", behavior: "smooth" });
    } else if (item.event === "done") {
      answerText = item.data.answer || answerText;
      if (item.data.code) answerText += `\n\n\`\`\`\n${item.data.code}\n\`\`\``;
      answer.innerHTML = renderMarkdown(answerText);
      answer.classList.remove("stream-cursor");
      progress.remove();
      elements.title.textContent = message.slice(0, 70);
      await refreshThreads().catch(renderThreadError);
    } else if (item.event === "error") {
      progress.remove();
      showError(item.data.message || "The request could not be completed.");
    }
  };

  try {
    const response = await fetch("/api/user-query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message, thread_id: currentThreadId }),
      signal: controller.signal,
    });
    if (!response.ok || !response.body) throw new Error("The server rejected the request.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() || "";
      for (const raw of events) await handleEvent(parseSseEvent(raw));
      if (done) break;
    }
    if (buffer.trim()) await handleEvent(parseSseEvent(buffer));
  } catch (error) {
    if (error.name === "AbortError") {
      progress.remove();
      answer.classList.remove("stream-cursor");
      if (answerText) answer.textContent += "\n\n[Response interrupted]";
      else answer.remove();
    } else {
      progress.remove();
      showError(error.message || "The request failed. Check that the API server is running.");
    }
  } finally {
    if (activeController === controller) {
      activeController = null;
      elements.send.disabled = false;
      elements.input.focus();
    }
  }
}

elements.newThread.addEventListener("click", resetConversation);
elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(elements.input.value);
});
elements.input.addEventListener("input", () => {
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 180)}px`;
});
elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});
document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    elements.input.value = button.dataset.prompt;
    elements.input.focus();
    elements.input.dispatchEvent(new Event("input"));
  });
});
document.querySelector("#open-sidebar").addEventListener("click", () => {
  elements.sidebar.classList.add("open");
  elements.scrim.classList.add("visible");
});
document.querySelector("#close-sidebar").addEventListener("click", closeSidebar);
elements.scrim.addEventListener("click", closeSidebar);
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    resetConversation();
    elements.input.focus();
  }
});

if (API_AVAILABLE) {
  refreshThreads().catch(renderThreadError);
} else {
  elements.connectionStatus.innerHTML = '<span class="status-dot offline"></span> Open server URL';
  renderThreadList([]);
  elements.threadList.firstElementChild.textContent = "Open the server URL shown by Uvicorn to load conversations.";
}
