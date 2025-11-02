let invoke;

async function initTauri() {
  // Ждем инициализации Tauri API (max 5 секунд)
  let attempts = 0;
  while ((!window.__TAURI__ || !window.__TAURI__.invoke) && attempts < 50) {
    await new Promise(resolve => setTimeout(resolve, 100));
    attempts++;
  }
  
  if (window.__TAURI__ && window.__TAURI__.invoke) {
    invoke = window.__TAURI__.invoke;
    console.log('✓ Tauri API инициализирован');
  } else {
    console.error('✗ Tauri API не найден');
    invoke = async () => { throw new Error('Tauri API не доступен'); };
  }
}

const themes = [
  {
    id: "graphite",
    name: "Graphite",
    values: {
      "--background": "#232528",
      "--foreground": "#f2f5f7",
      "--muted": "#8f9aa5",
      "--surface": "#2d3034",
      "--accent": "#6c9ef8",
      "--border": "#3c4046"
    }
  },
  {
    id: "dusk",
    name: "Dusk",
    values: {
      "--background": "#1d1f24",
      "--foreground": "#f8f9fb",
      "--muted": "#838b95",
      "--surface": "#272a31",
      "--accent": "#ff866c",
      "--border": "#383b44"
    }
  },
  {
    id: "light",
    name: "Light",
    values: {
      "--background": "#f7f8fb",
      "--foreground": "#1f2227",
      "--muted": "#59616d",
      "--surface": "#ffffff",
      "--accent": "#4867f4",
      "--border": "#d7dbe4"
    }
  }
];

const slashMenuItems = [
  {
    id: "settings",
    title: "Настройки",
    items: [
      {
        id: "settings-theme",
        label: "Темы",
        hint: "Выбор цветовой схемы",
        action: () => openSettings()
      },
      {
        id: "settings-font",
        label: "Шрифты",
        hint: "Настройка гарнитуры и размера",
        action: () => openSettings("fonts")
      },
      {
        id: "settings-ollama",
        label: "Ollama",
        hint: "Параметры локальной LLM",
        action: () => openSettings("ollama")
      }
    ]
  },
  {
    id: "modes",
    title: "Режимы",
    items: [
      {
        id: "mode-terminal",
        label: "Терминал",
        hint: "Выполнение команд",
        action: () => setMode("terminal")
      },
      {
        id: "mode-ide",
        label: "IDE",
        hint: "Работа с файлами",
        action: () => setMode("ide")
      },
      {
        id: "mode-chat",
        label: "Чат",
        hint: "Диалог с моделью",
        action: () => setMode("chat")
      },
      {
        id: "mode-agent",
        label: "Agent",
        hint: "Полуавтоматический режим",
        action: () => setMode("agent")
      }
    ]
  }
];

const state = {
  settings: null,
  mode: "terminal",
  slashMenuOpen: false,
  slashMenuItems: [],
  slashSelection: null,
  commandHistory: [],
  historyIndex: -1,
  currentDir: null,
  fileTree: [],
  selectedFile: null
};

const selectors = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  await initTauri();
  cacheDom();
  bindEvents();
  await loadSettings();
  renderThemes();
  updateTheme(state.settings.theme_id);
  setMode(state.settings.mode, { silent: true });
  selectors.commandInput.focus();
}

function cacheDom() {
  selectors.workspace = document.getElementById("workspace");
  selectors.terminalView = document.getElementById("terminal-view");
  selectors.chatView = document.getElementById("chat-view");
  selectors.ideView = document.getElementById("ide-view");
  selectors.currentDir = document.getElementById("current-dir");
  selectors.commandForm = document.getElementById("command-form");
  selectors.commandInput = document.getElementById("command-input");
  selectors.terminalOutput = document.getElementById("terminal-output");
  selectors.chatOutput = document.getElementById("chat-output");
  selectors.chatModel = document.getElementById("chat-model");
  selectors.slashMenu = document.getElementById("slash-menu");
  selectors.slashGroupTpl = document.getElementById("slash-menu-template");
  selectors.slashItemTpl = document.getElementById("slash-menu-item-template");
  selectors.settingsOverlay = document.getElementById("settings-overlay");
  selectors.settingsClose = document.getElementById("settings-close");
  selectors.settingsSave = document.getElementById("settings-save");
  selectors.themeOptions = document.getElementById("theme-options");
  selectors.fontFamily = document.getElementById("font-family");
  selectors.fontSize = document.getElementById("font-size");
  selectors.ollamaModel = document.getElementById("ollama-model");
  selectors.ollamaTemperature = document.getElementById("ollama-temperature");
  selectors.fileTree = document.getElementById("file-tree");
  selectors.editor = document.getElementById("editor");
  selectors.editorFilename = document.getElementById("editor-filename");
  selectors.editorContent = document.getElementById("editor-content");
  selectors.idePath = document.getElementById("ide-path");
}

function bindEvents() {
  selectors.commandForm.addEventListener("submit", onCommandSubmit);
  selectors.commandInput.addEventListener("input", onCommandInput);
  selectors.commandInput.addEventListener("keydown", onCommandKeyDown);
  selectors.settingsClose.addEventListener("click", () => closeSettings());
  selectors.settingsOverlay.addEventListener("click", (event) => {
    if (event.target === selectors.settingsOverlay) {
      closeSettings();
    }
  });
  selectors.settingsSave.addEventListener("click", persistSettings);
}

async function loadSettings() {
  try {
    const settings = await invoke("get_settings");
    state.settings = settings;
    selectors.fontFamily.value = settings.font_family;
    selectors.fontSize.value = settings.font_size;
    selectors.ollamaModel.value = settings.ollama.model;
    selectors.ollamaTemperature.value = settings.ollama.temperature;
    selectors.chatModel.textContent = `Модель: ${settings.ollama.model}`;
  } catch (error) {
    console.error("Не удалось загрузить настройки", error);
    state.settings = {
      theme_id: "graphite",
      font_family: "IBM Plex Mono",
      font_size: 15,
      mode: "terminal",
      ollama: { model: "llama3", temperature: 0.4 }
    };
  }
}

function renderThemes() {
  selectors.themeOptions.innerHTML = "";
  themes.forEach((theme) => {
    const element = document.createElement("button");
    element.type = "button";
    element.className = "theme-option";
    element.dataset.themeId = theme.id;
    element.innerHTML = `
      <div class="theme-option__preview" style="background: ${theme.values["--surface"]};"></div>
      <div>${theme.name}</div>
    `;
    if (theme.id === state.settings.theme_id) {
      element.classList.add("is-active");
    }
    element.addEventListener("click", () => {
      document
        .querySelectorAll(".theme-option")
        .forEach((item) => item.classList.remove("is-active"));
      element.classList.add("is-active");
      updateTheme(theme.id);
    });
    selectors.themeOptions.appendChild(element);
  });
}

function updateTheme(themeId) {
  const theme = themes.find((t) => t.id === themeId) || themes[0];
  Object.entries(theme.values).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value);
  });
  document.body.style.fontFamily = state.settings.font_family;
  document.body.style.fontSize = `${state.settings.font_size}px`;
  state.settings.theme_id = theme.id;
}

async function onCommandSubmit(event) {
  event.preventDefault();
  const value = selectors.commandInput.value.trim();
  if (!value) {
    closeSlashMenu();
    return;
  }

  closeSlashMenu();
  appendHistory(value);
  selectors.commandInput.value = "";

  if (state.mode === "terminal" || value.startsWith("!")) {
    await handleTerminalCommand(value.startsWith("!") ? value.slice(1) : value);
  } else {
    await handlePrompt(value);
  }
}

async function handleTerminalCommand(command) {
  const placeholder = renderTerminalEntry({ command, status: "Выполняется..." });
  try {
    const result = await invoke("run_terminal_command", { command });
    updateTerminalEntry(placeholder, {
      command,
      stdout: result.stdout,
      stderr: result.stderr,
      code: result.code,
      currentDir: result.current_dir
    });

    if (result.current_dir) {
      state.currentDir = result.current_dir;
      selectors.currentDir.textContent = result.current_dir;
    }

    if (result.file_tree && result.file_tree.length) {
      state.fileTree = result.file_tree;
      renderFileTree();
      selectors.idePath.textContent = result.current_dir || "";
      if (state.mode !== "ide") {
        setMode("ide");
      }
    }
  } catch (error) {
    console.error(error);
    updateTerminalEntry(placeholder, { command, stderr: String(error) });
  }
}

async function handlePrompt(prompt) {
  pushChatMessage("user", prompt);
  try {
    const payload = {
      prompt,
      mode: state.mode,
      model: state.settings.ollama.model,
      temperature: state.settings.ollama.temperature
    };
    const response = await invoke("query_ollama", payload);
    selectors.chatModel.textContent = `Модель: ${state.settings.ollama.model}`;
    pushChatMessage("assistant", response.message);
  } catch (error) {
    pushChatMessage("assistant", `Ошибка: ${error}`);
  }
}

function renderTerminalEntry({ command, stdout, stderr, status, code, currentDir }) {
  const container = document.createElement("div");
  container.className = "terminal-entry";
  updateTerminalEntry(container, { command, stdout, stderr, status, code, currentDir });
  selectors.terminalOutput.appendChild(container);
  selectors.terminalOutput.scrollTop = selectors.terminalOutput.scrollHeight;
  return container;
}

function updateTerminalEntry(node, { command, stdout, stderr, status, code, currentDir }) {
  node.innerHTML = `
    <div class="terminal-entry__command">$ ${command}</div>
    ${status ? `<div class="caption">${status}</div>` : ""}
    ${stdout ? `<pre>${escapeHtml(stdout)}</pre>` : ""}
    ${stderr ? `<pre class="caption">${escapeHtml(stderr)}</pre>` : ""}
    ${code !== undefined && code !== null ? `<div class="caption">Код выхода: ${code}</div>` : ""}
    ${currentDir ? `<div class="caption">Текущий каталог: ${currentDir}</div>` : ""}
  `;
  selectors.terminalOutput.scrollTop = selectors.terminalOutput.scrollHeight;
}

function pushChatMessage(role, text) {
  const message = document.createElement("div");
  message.className = `chat-message chat-message--${role === "user" ? "user" : "assistant"}`;
  message.innerHTML = `
    <div class="chat-message__role">${role === "user" ? "Пользователь" : "Модель"}</div>
    <div>${escapeHtml(text)}</div>
  `;
  selectors.chatOutput.appendChild(message);
  selectors.chatOutput.scrollTop = selectors.chatOutput.scrollHeight;
}

function appendHistory(command) {
  state.commandHistory.unshift(command);
  state.commandHistory = state.commandHistory.slice(0, 50);
  state.historyIndex = -1;
}

async function onCommandKeyDown(event) {
  if (state.slashMenuOpen) {
    if (event.key === "ArrowDown" || event.key === "Tab") {
      event.preventDefault();
      moveSlashSelection(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveSlashSelection(-1);
    } else if (event.key === "Enter") {
      if (state.slashSelection) {
        event.preventDefault();
        state.slashSelection.action();
        closeSlashMenu();
        selectors.commandInput.value = "";
      }
    } else if (event.key === "Escape") {
      closeSlashMenu();
    }
    return;
  }

  if (event.key === "ArrowUp") {
    event.preventDefault();
    navigateHistory(1);
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    navigateHistory(-1);
  }
}

function navigateHistory(direction) {
  const maxIndex = state.commandHistory.length - 1;
  if (maxIndex < 0) {
    return;
  }
  if (state.historyIndex === -1) {
    state.historyIndex = 0;
  } else {
    state.historyIndex = Math.min(Math.max(state.historyIndex + direction, 0), maxIndex);
  }
  selectors.commandInput.value = state.commandHistory[state.historyIndex] || "";
}

function onCommandInput(event) {
  const value = event.target.value;
  if (value.startsWith("/")) {
    openSlashMenu(value.slice(1));
  } else {
    closeSlashMenu();
  }
}

function openSlashMenu(query = "") {
  state.slashMenuOpen = true;
  selectors.slashMenu.innerHTML = "";
  selectors.slashMenu.classList.remove("hidden");

  const normalized = query.trim().toLowerCase();
  const entries = slashMenuItems.map((group) => ({
    title: group.title,
    items: group.items.filter((item) =>
      !normalized || item.label.toLowerCase().includes(normalized) || item.hint.toLowerCase().includes(normalized)
    )
  })).filter((group) => group.items.length);

  if (!entries.length) {
    const placeholder = document.createElement("div");
    placeholder.className = "caption";
    placeholder.textContent = "Нет совпадений";
    selectors.slashMenu.appendChild(placeholder);
    state.slashSelection = null;
    return;
  }

  const fragment = document.createDocumentFragment();
  entries.forEach((group) => {
    const groupNode = selectors.slashGroupTpl.content.firstElementChild.cloneNode(true);
    groupNode.querySelector(".slash-menu__title").textContent = group.title;
    const itemsContainer = groupNode.querySelector(".slash-menu__items");
    group.items.forEach((item) => {
      const itemNode = selectors.slashItemTpl.content.firstElementChild.cloneNode(true);
      itemNode.innerHTML = `
        <span>${item.label}</span>
        <span class="caption">${item.hint}</span>
      `;
      itemNode.addEventListener("click", () => {
        item.action();
        closeSlashMenu();
        selectors.commandInput.value = "";
      });
      itemNode.dataset.itemId = item.id;
      itemsContainer.appendChild(itemNode);
    });
    fragment.appendChild(groupNode);
  });
  selectors.slashMenu.appendChild(fragment);
  state.slashMenuItems = Array.from(selectors.slashMenu.querySelectorAll(".slash-menu__item"));
  moveSlashSelection(0);
}

function moveSlashSelection(delta) {
  if (!state.slashMenuItems.length) {
    state.slashSelection = null;
    return;
  }
  let index = state.slashSelection ? state.slashMenuItems.indexOf(state.slashSelection.node) : -1;
  index = (index + delta + state.slashMenuItems.length) % state.slashMenuItems.length;
  const node = state.slashMenuItems[index];
  state.slashMenuItems.forEach((item) => item.classList.remove("is-active"));
  node.classList.add("is-active");
  const id = node.dataset.itemId;
  const item = findSlashItemById(id);
  state.slashSelection = { node, action: item?.action };
}

function findSlashItemById(id) {
  for (const group of slashMenuItems) {
    for (const item of group.items) {
      if (item.id === id) {
        return item;
      }
    }
  }
  return null;
}

function closeSlashMenu() {
  selectors.slashMenu.classList.add("hidden");
  state.slashMenuOpen = false;
  state.slashMenuItems = [];
  state.slashSelection = null;
}

function openSettings(section) {
  selectors.settingsOverlay.classList.remove("hidden");
  selectors.settingsOverlay.dataset.section = section || "";
}

function closeSettings() {
  selectors.settingsOverlay.classList.add("hidden");
}

async function persistSettings() {
  const payload = {
    theme_id: state.settings.theme_id,
    font_family: selectors.fontFamily.value || state.settings.font_family,
    font_size: Number(selectors.fontSize.value) || state.settings.font_size,
    mode: state.mode,
    ollama: {
      model: selectors.ollamaModel.value || state.settings.ollama.model,
      temperature: Number(selectors.ollamaTemperature.value) || state.settings.ollama.temperature
    }
  };

  try {
    const updated = await invoke("update_settings", { data: payload });
    state.settings = updated;
    selectors.chatModel.textContent = `Модель: ${updated.ollama.model}`;
    document.body.style.fontFamily = updated.font_family;
    document.body.style.fontSize = `${updated.font_size}px`;
    closeSettings();
  } catch (error) {
    console.error("Не удалось сохранить настройки", error);
  }
}

function setMode(mode, options = {}) {
  state.mode = mode;
  [selectors.terminalView, selectors.chatView, selectors.ideView].forEach((view) => view.classList.add("hidden"));
  if (mode === "terminal") {
    selectors.terminalView.classList.remove("hidden");
  } else if (mode === "chat" || mode === "agent") {
    selectors.chatView.classList.remove("hidden");
  } else if (mode === "ide") {
    selectors.ideView.classList.remove("hidden");
  }

  if (!options.silent) {
    invoke("update_settings", { data: { mode } }).catch((error) => console.error(error));
  }
}

function renderFileTree() {
  selectors.fileTree.innerHTML = "";
  const fragment = document.createDocumentFragment();
  state.fileTree.forEach((node) => {
    fragment.appendChild(createFileNode(node));
  });
  selectors.fileTree.appendChild(fragment);
}

function createFileNode(node) {
  const container = document.createElement("div");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "file-node";
  button.dataset.path = node.path;
  button.textContent = node.is_dir ? `📁 ${node.name}` : `📄 ${node.name}`;
  button.addEventListener("click", () => onFileNodeClick(node));
  container.appendChild(button);
  if (node.children && node.children.length) {
    const children = document.createElement("div");
    children.className = "file-node__children";
    node.children.forEach((child) => {
      children.appendChild(createFileNode(child));
    });
    container.appendChild(children);
  }
  return container;
}

async function onFileNodeClick(node) {
  if (node.is_dir) {
    return;
  }
  try {
    const content = await invoke("read_file", { path: node.path });
    selectors.editorFilename.textContent = node.path;
    selectors.editorContent.textContent = content;
    Array.from(selectors.fileTree.querySelectorAll(".file-node"))
      .forEach((el) => el.classList.remove("is-active"));
    const active = selectors.fileTree.querySelector(`[data-path="${cssEscape(node.path)}"]`);
    if (active) {
      active.classList.add("is-active");
    }
  } catch (error) {
    selectors.editorContent.textContent = `Не удалось загрузить файл: ${error}`;
  }
}

function cssEscape(value) {
  return value.replace(/"/g, "\\\"");
}

function escapeHtml(text = "") {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

