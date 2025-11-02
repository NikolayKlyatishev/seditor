import { invoke } from '@tauri-apps/api/tauri';

async function initTauri() {
  console.log('✓ Tauri API инициализирован');
}

// Список команд для автодополнения
const terminalCommands = [
  // Навигация
  'cd', 'ls', 'pwd', 'tree',
  // Файловые операации
  'cat', 'touch', 'mkdir', 'rm', 'cp', 'mv', 'chmod', 'chown',
  // Поиск
  'find', 'grep', 'locate',
  // Текстовые редакторы
  'nano', 'vim', 'vi',
  // Системные
  'ps', 'top', 'kill', 'df', 'du', 'free', 'uname',
  // Git
  'git status', 'git add', 'git commit', 'git push', 'git pull', 'git log', 'git diff', 'git branch', 'git checkout', 'git merge',
  // Node/npm
  'npm install', 'npm run', 'npm start', 'npm test', 'npm build', 'node',
  // Cargo/Rust
  'cargo build', 'cargo run', 'cargo test', 'cargo check', 'cargo clean',
  // Другие
  'echo', 'clear', 'history', 'man', 'which', 'whereis'
];

const themes = [
  {
    id: "graphite",
    name: "Terminal Black",
    values: {
      "--background": "#0a0a0a",
      "--foreground": "#ffffff",
      "--muted": "#888888",
      "--surface": "#1a1a1a",
      "--surface-light": "#2a2a2a",
      "--accent": "#00ff88",
      "--border": "#333333",
      "--glow": "rgba(0, 255, 136, 0.3)"
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
  selectedFile: null,
  autocompleteOpen: false,
  autocompleteItems: [],
  autocompleteSelection: 0,
  autocompleteBasePath: '',
  autocompletePrefix: ''
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
  selectors.autocompleteMenu = document.getElementById("autocomplete-menu");
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
  // Обработка команды clear
  if (command.trim() === 'clear') {
    selectors.terminalOutput.innerHTML = '';
    return;
  }
  
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
  // Автоскролл с небольшой задержкой для корректного рендеринга
  requestAnimationFrame(() => {
    selectors.terminalOutput.scrollTop = selectors.terminalOutput.scrollHeight;
  });
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
  // Автоскролл с небольшой задержкой для корректного рендеринга
  requestAnimationFrame(() => {
    selectors.terminalOutput.scrollTop = selectors.terminalOutput.scrollHeight;
  });
}

function pushChatMessage(role, text) {
  const message = document.createElement("div");
  message.className = `chat-message chat-message--${role === "user" ? "user" : "assistant"}`;
  message.innerHTML = `
    <div class="chat-message__role">${role === "user" ? "Пользователь" : "Модель"}</div>
    <div>${escapeHtml(text)}</div>
  `;
  selectors.chatOutput.appendChild(message);
  // Автоскролл с небольшой задержкой для корректного рендеринга
  requestAnimationFrame(() => {
    selectors.chatOutput.scrollTop = selectors.chatOutput.scrollHeight;
  });
}

function appendHistory(command) {
  state.commandHistory.unshift(command);
  state.commandHistory = state.commandHistory.slice(0, 50);
  state.historyIndex = -1;
}

async function onCommandKeyDown(event) {
  // Ctrl/Cmd + T - вернуться в терминал
  if ((event.ctrlKey || event.metaKey) && event.key === 't') {
    event.preventDefault();
    setMode("terminal");
    return;
  }

  // Ctrl/Cmd + Q - выйти из IDE в терминал
  if ((event.ctrlKey || event.metaKey) && event.key === 'q') {
    event.preventDefault();
    if (state.mode === 'ide') {
      setMode("terminal");
    }
    return;
  }

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

  if (state.autocompleteOpen) {
    if (event.key === "ArrowDown" || event.key === "Tab") {
      event.preventDefault();
      moveAutocompleteSelection(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveAutocompleteSelection(-1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveAutocompleteSelection(-5);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      moveAutocompleteSelection(5);
    } else if (event.key === "Enter") {
      event.preventDefault();
      selectAutocompleteItem();
    } else if (event.key === "Escape") {
      closeAutocompleteMenu();
    }
    return;
  }

  // Tab автодополнение в терминальном режиме
  if (event.key === "Tab" && state.mode === "terminal") {
    event.preventDefault();
    await handleTabCompletion();
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

async function handleTabCompletion() {
  const input = selectors.commandInput.value;
  
  // Проверяем, это команда cd с путем?
  const cdMatch = input.match(/^cd\s+(.*)$/);
  if (cdMatch) {
    await showAutocompleteMenu(cdMatch[1]);
    return;
  }
  
  // Обычное автодополнение команд (без визуального меню)
  const matches = terminalCommands.filter(cmd => 
    cmd.startsWith(input.toLowerCase())
  );
  
  if (matches.length === 0) {
    return;
  }
  
  if (matches.length === 1) {
    selectors.commandInput.value = matches[0] + ' ';
    return;
  }
  
  // Для нескольких совпадений можно показать меню или циклически переключать
  // Пока просто подставляем первое
  selectors.commandInput.value = matches[0] + ' ';
}

async function showAutocompleteMenu(pathPrefix) {
  try {
    const dirs = await invoke("get_directories", { prefix: pathPrefix });
    
    if (dirs.length === 0) {
      closeAutocompleteMenu();
      return;
    }
    
    state.autocompleteOpen = true;
    state.autocompleteItems = dirs;
    state.autocompleteSelection = 0;
    state.autocompleteBasePath = pathPrefix;
    state.autocompletePrefix = pathPrefix;
    
    renderAutocompleteMenu();
  } catch (error) {
    console.error("Ошибка автодополнения:", error);
    closeAutocompleteMenu();
  }
}

function renderAutocompleteMenu() {
  selectors.autocompleteMenu.innerHTML = "";
  selectors.autocompleteMenu.classList.remove("hidden");
  
  state.autocompleteItems.forEach((dir, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "autocomplete-menu__item";
    if (index === state.autocompleteSelection) {
      item.classList.add("is-active");
    }
    item.textContent = dir;
    item.addEventListener("click", () => {
      state.autocompleteSelection = index;
      selectAutocompleteItem();
    });
    selectors.autocompleteMenu.appendChild(item);
  });
}

function moveAutocompleteSelection(delta) {
  if (state.autocompleteItems.length === 0) return;
  
  state.autocompleteSelection = (state.autocompleteSelection + delta + state.autocompleteItems.length) % state.autocompleteItems.length;
  renderAutocompleteMenu();
}

async function selectAutocompleteItem() {
  if (state.autocompleteItems.length === 0) return;
  
  const selectedDir = state.autocompleteItems[state.autocompleteSelection];
  
  // Формируем новый путь
  const basePath = state.autocompleteBasePath;
  let newPath;
  
  if (basePath.endsWith('/')) {
    newPath = basePath + selectedDir;
  } else {
    // Убираем последнюю часть пути и добавляем выбранную директорию
    const parts = basePath.split('/');
    parts[parts.length - 1] = selectedDir;
    newPath = parts.join('/');
  }
  
  // Обновляем ввод
  selectors.commandInput.value = `cd ${newPath}/`;
  
  // Загружаем поддиректории для продолжения навигации
  await showAutocompleteMenu(newPath + '/');
}

function closeAutocompleteMenu() {
  state.autocompleteOpen = false;
  state.autocompleteItems = [];
  state.autocompleteSelection = 0;
  selectors.autocompleteMenu.classList.add("hidden");
  selectors.autocompleteMenu.innerHTML = "";
}

function onCommandInput(event) {
  const value = event.target.value;
  
  // Закрываем автодополнение при изменении ввода (кроме программного изменения)
  if (event.inputType && state.autocompleteOpen) {
    closeAutocompleteMenu();
  }
  
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
    
    // Добавляем индикатор в первую группу
    if (entries.indexOf(group) === 0) {
      const indicator = document.createElement("div");
      indicator.className = "selection-indicator";
      indicator.id = "slash-menu-indicator";
      itemsContainer.appendChild(indicator);
    }
    
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
  
  // Перемещаем индикатор к активному элементу
  moveIndicator(node, "slash-menu-indicator");
  
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

async function setMode(mode, options = {}) {
  state.mode = mode;
  [selectors.terminalView, selectors.chatView, selectors.ideView].forEach((view) => view.classList.add("hidden"));
  if (mode === "terminal") {
    selectors.terminalView.classList.remove("hidden");
  } else if (mode === "chat" || mode === "agent") {
    selectors.chatView.classList.remove("hidden");
  } else if (mode === "ide") {
    selectors.ideView.classList.remove("hidden");
    
    // Загружаем дерево файлов текущего каталога, если его ещё нет
    if (!state.fileTree || state.fileTree.length === 0) {
      try {
        const result = await invoke("run_terminal_command", { command: "cd ." });
        if (result.file_tree && result.file_tree.length) {
          state.fileTree = result.file_tree;
          renderFileTree();
          selectors.idePath.textContent = result.current_dir || state.currentDir;
        }
      } catch (error) {
        console.error("Не удалось загрузить дерево файлов:", error);
      }
    }
  }

  // Обновляем placeholder в зависимости от режима
  const modeNames = {
    terminal: "Терминал",
    ide: "IDE",
    chat: "Чат",
    agent: "Agent"
  };
  const currentModeName = modeNames[mode] || "Терминал";
  const shortcuts = mode === 'ide' ? '/ - меню, Ctrl+Q - выход' : '/ - меню, Ctrl+T - терминал';
  selectors.commandInput.placeholder = `${currentModeName} режим (${shortcuts})`;

  if (!options.silent) {
    invoke("update_settings", { data: { mode } }).catch((error) => console.error(error));
  }
}

function renderFileTree() {
  selectors.fileTree.innerHTML = "";
  
  // Создаём индикатор выбора
  const indicator = document.createElement("div");
  indicator.className = "selection-indicator";
  indicator.id = "file-tree-indicator";
  selectors.fileTree.appendChild(indicator);
  
  const fragment = document.createDocumentFragment();
  state.fileTree.forEach((node) => {
    fragment.appendChild(createFileNode(node));
  });
  selectors.fileTree.appendChild(fragment);
}

// Функция для перемещения индикатора к элементу
function moveIndicator(element, indicatorId) {
  const indicator = document.getElementById(indicatorId);
  if (!indicator || !element) return;
  
  const container = indicator.parentElement;
  const containerRect = container.getBoundingClientRect();
  const elementRect = element.getBoundingClientRect();
  
  const top = elementRect.top - containerRect.top + container.scrollTop;
  const height = elementRect.height;
  
  indicator.style.top = `${top}px`;
  indicator.style.height = `${height}px`;
  indicator.classList.add('visible');
}

function createFileNode(node) {
  const container = document.createElement("div");
  container.className = "file-node-container";
  
  const button = document.createElement("button");
  button.type = "button";
  button.className = "file-node";
  button.dataset.path = node.path;
  
  // Добавляем иконку для директорий
  if (node.is_dir) {
    const icon = document.createElement("span");
    icon.className = "file-node__icon";
    icon.textContent = "▶";
    button.appendChild(icon);
    button.insertAdjacentText("beforeend", ` ${node.name}`);
    
    // Создаём контейнер для дочерних элементов (даже если их пока нет)
    const children = document.createElement("div");
    children.className = "file-node__children";
    children.style.display = "none"; // Скрыто по умолчанию
    
    // Если есть предзагруженные дочерние элементы, добавляем их
    if (node.children && node.children.length) {
      node.children.forEach((child) => {
        children.appendChild(createFileNode(child));
      });
      node.childrenLoaded = true;
    }
    
    container.appendChild(button);
    container.appendChild(children);
  } else {
    button.textContent = `  ${node.name}`;
    container.appendChild(button);
  }
  
  button.addEventListener("click", () => onFileNodeClick(node, container, button));
  
  return container;
}

async function onFileNodeClick(node, container, button) {
  if (node.is_dir) {
    const childrenContainer = container.querySelector(".file-node__children");
    const icon = button.querySelector(".file-node__icon");
    
    if (childrenContainer) {
      const isExpanded = childrenContainer.style.display !== "none";
      
      if (isExpanded) {
        // Сворачиваем
        childrenContainer.style.display = "none";
        if (icon) {
          icon.style.transform = "rotate(0deg)";
        }
      } else {
        // Разворачиваем
        // Если дочерние элементы не загружены (пустой контейнер), загружаем их
        if (childrenContainer.children.length === 0 || !node.childrenLoaded) {
          try {
            // Загружаем содержимое каталога
            const result = await invoke("run_terminal_command", { command: `ls -la "${node.path}"` });
            
            // Парсим вывод ls и создаём узлы
            // Но лучше использовать специальную команду для получения дерева
            // Попробуем получить через cd
            const treeResult = await loadDirectoryContents(node.path);
            
            if (treeResult && treeResult.length > 0) {
              childrenContainer.innerHTML = "";
              treeResult.forEach((child) => {
                childrenContainer.appendChild(createFileNode(child));
              });
              node.childrenLoaded = true;
            }
          } catch (error) {
            console.error("Не удалось загрузить содержимое каталога:", error);
          }
        }
        
        childrenContainer.style.display = "flex";
        if (icon) {
          icon.style.transform = "rotate(90deg)";
        }
      }
    }
    return;
  }
  
  // Открываем файл
  try {
    const content = await invoke("read_file", { path: node.path });
    selectors.editorFilename.textContent = node.path;
    
    // Определяем язык по расширению файла
    const language = detectLanguage(node.name);
    
    // Применяем подсветку синтаксиса
    if (language && window.Prism && Prism.languages[language]) {
      try {
        const highlighted = Prism.highlight(content, Prism.languages[language], language);
        selectors.editorContent.innerHTML = highlighted;
        selectors.editorContent.className = `editor__body language-${language}`;
      } catch (err) {
        // Если подсветка не удалась, показываем plain text
        console.warn(`Ошибка подсветки для ${language}:`, err);
        selectors.editorContent.textContent = content;
        selectors.editorContent.className = 'editor__body';
      }
    } else {
      selectors.editorContent.textContent = content;
      selectors.editorContent.className = 'editor__body';
    }
    
    Array.from(selectors.fileTree.querySelectorAll(".file-node"))
      .forEach((el) => el.classList.remove("is-active"));
    const active = selectors.fileTree.querySelector(`[data-path="${cssEscape(node.path)}"]`);
    if (active) {
      active.classList.add("is-active");
      moveIndicator(active, "file-tree-indicator");
    }
  } catch (error) {
    selectors.editorContent.textContent = `Не удалось загрузить файл: ${error}`;
  }
}

function detectLanguage(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const languageMap = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'py': 'python',
    'rs': 'rust',
    'java': 'java',
    'cs': 'csharp',
    'json': 'json',
    'css': 'css',
    'scss': 'css',
    'html': 'markup',
    'xml': 'markup',
    'md': 'markdown',
    'sh': 'bash',
    'bash': 'bash',
    'zsh': 'bash',
    'toml': 'toml',
    'yaml': 'yaml',
    'yml': 'yaml'
  };
  return languageMap[ext] || null;
}

async function loadDirectoryContents(dirPath) {
  try {
    // Используем специальную команду для получения содержимого каталога
    const fileTree = await invoke("get_directory_tree", { path: dirPath });
    return fileTree || [];
  } catch (error) {
    console.error("Ошибка загрузки каталога:", error);
    return [];
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

