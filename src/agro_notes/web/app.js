(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const messagesRoot = $("#messages");
  const composer = $("#composer");
  const messageInput = $("#message-input");
  const statusBox = $("#status");
  const attachmentPreview = $("#attachment-preview");
  const photoInput = $("#photo-input");
  const audioInput = $("#audio-input");
  const MAX_ATTACHMENTS = 5;
  const MAX_FILE_BYTES = 4 * 1024 * 1024;
  const MAX_TOTAL_BYTES = 10 * 1024 * 1024;
  const MAX_RECORDING_MS = 120_000;
  const ALLOWED_AUDIO_TYPES = new Set(["audio/aac", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav", "audio/webm", "audio/x-m4a"]);
  let attachments = [];
  let inFlight = false;
  let mediaRecorder = null;
  let recordingStream = null;
  let recordingChunks = [];
  let recordingBytes = 0;
  let recordingRejected = false;
  let recordingTimer = null;

  function setStatus(message) {
    statusBox.textContent = message;
  }

  async function api(path, body) {
    const response = await fetch(path, body ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    } : { headers: { Accept: "application/json" } });
    let data;
    try { data = await response.json(); }
    catch { throw new Error(`Resposta inválida do servidor (HTTP ${response.status}).`); }
    if (!response.ok || data.ok === false) throw new Error(data.error || `Falha HTTP ${response.status}.`);
    return data;
  }

  function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  function attachmentDataUrl(attachment) {
    if (attachment.url) return attachment.url;
    return `data:${attachment.mime_type};base64,${attachment.data}`;
  }

  function renderAttachment(attachment) {
    const card = document.createElement("div");
    card.className = "attachment-card";
    const mime = String(attachment.mime_type || "");
    const dataUrl = attachmentDataUrl(attachment);
    if (mime.startsWith("image/")) {
      const image = document.createElement("img");
      image.src = dataUrl;
      image.alt = `Foto anexada: ${attachment.filename || "imagem"}`;
      image.loading = "lazy";
      card.append(image);
    } else if (mime.startsWith("audio/")) {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "metadata";
      audio.src = dataUrl;
      audio.setAttribute("aria-label", `Áudio anexado: ${attachment.filename || "gravação"}`);
      card.append(audio);
    } else {
      const unsupported = document.createElement("p");
      unsupported.className = "attachment-caption";
      unsupported.textContent = "Tipo de mídia não reconhecido.";
      card.append(unsupported);
    }
    const caption = document.createElement("div");
    caption.className = "attachment-caption";
    const name = document.createElement("strong");
    name.textContent = attachment.filename || "Anexo";
    const state = document.createElement("span");
    state.className = "attachment-state";
    state.textContent = mime.startsWith("audio/") ? "Recebido · sem transcrição" : "Recebida · sem análise";
    caption.append(name, state);
    card.append(caption);
    return card;
  }

  function renderMessage(message) {
    const isUser = message.role === "user";
    const article = document.createElement("article");
    article.className = `message ${isUser ? "user-message" : "assistant-message"}`;
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = isUser ? "V" : "A";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (message.text) {
      const paragraph = document.createElement("p");
      paragraph.textContent = message.text;
      bubble.append(paragraph);
    }
    if (Array.isArray(message.attachments) && message.attachments.length) {
      const list = document.createElement("div");
      list.className = "attachment-list";
      message.attachments.forEach((attachment) => list.append(renderAttachment(attachment)));
      bubble.append(list);
    }
    if (!isUser && message.document) {
      const proposal = document.createElement("details");
      proposal.className = "proposal-summary";
      const summary = document.createElement("summary");
      summary.textContent = "Ver proposta estruturada";
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(message.document, null, 2);
      proposal.append(summary, pre);
      bubble.append(proposal);
    }
    if (!isUser && message.pending_id && message.state === "WAITING_CONFIRMATION") {
      const actions = document.createElement("div");
      actions.className = "proposal-actions";
      for (const [action, label, className] of [
        ["cancel", "Cancelar", "button button-cancel"],
        ["confirm", "Confirmar registro", "button button-confirm"],
      ]) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = className;
        button.dataset.action = action;
        button.dataset.pendingId = message.pending_id;
        button.textContent = label;
        actions.append(button);
      }
      bubble.append(actions);
    }
    const time = document.createElement("span");
    time.className = "message-time";
    time.textContent = formatTime(message.created_at);
    bubble.append(time);
    article.append(avatar, bubble);
    messagesRoot.append(article);
  }

  function renderMessages(messages, replace = false) {
    const welcome = $(".welcome-message");
    if (!Array.isArray(messages)) return;
    if (replace) messagesRoot.replaceChildren();
    if (!messages.length) return;
    messages.forEach(renderMessage);
    messagesRoot.scrollTop = messagesRoot.scrollHeight;
    if (welcome) welcome.remove();
  }

  function updateAttachmentPreview() {
    attachmentPreview.replaceChildren();
    attachmentPreview.hidden = attachments.length === 0;
    attachments.forEach((entry, index) => {
      const chip = document.createElement("div");
      chip.className = "attachment-chip";
      const type = document.createElement("span");
      type.setAttribute("aria-hidden", "true");
      type.textContent = entry.file.type.startsWith("image/") ? "▧" : "♫";
      const name = document.createElement("span");
      name.className = "attachment-chip-name";
      name.textContent = entry.file.name;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-attachment";
      remove.dataset.removeAttachment = String(index);
      remove.setAttribute("aria-label", `Remover ${entry.file.name}`);
      remove.textContent = "×";
      chip.append(type, name, remove);
      attachmentPreview.append(chip);
    });
  }

  function addFiles(fileList) {
    const selected = Array.from(fileList || []);
    let totalBytes = attachments.reduce((total, item) => total + item.file.size, 0);
    for (const file of selected) {
      if (attachments.length >= MAX_ATTACHMENTS) {
        setStatus(`Limite de ${MAX_ATTACHMENTS} anexos por mensagem.`);
        break;
      }
      const isImage = file.type.startsWith("image/") && file.type !== "image/svg+xml";
      const isAudio = ALLOWED_AUDIO_TYPES.has(file.type.split(";", 1)[0].toLowerCase());
      if (!(isImage || isAudio)) {
        setStatus(`${file.name}: selecione uma imagem ou um arquivo de áudio.`);
        continue;
      }
      if (file.size > MAX_FILE_BYTES) {
        setStatus(`${file.name}: cada anexo deve ter até 4 MB.`);
        continue;
      }
      if (totalBytes + file.size > MAX_TOTAL_BYTES) {
        setStatus("Os anexos podem somar até 10 MB por mensagem.");
        continue;
      }
      attachments.push({ file, url: URL.createObjectURL(file) });
      totalBytes += file.size;
    }
    updateAttachmentPreview();
    if (attachments.length) setStatus(`${attachments.length} anexo(s) pronto(s) para enviar.`);
  }

  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
      reader.onerror = () => reject(new Error(`Não consegui ler ${file.name}.`));
      reader.readAsDataURL(file);
    });
  }

  function setBusy(busy) {
    inFlight = busy;
    $("#send-button").disabled = busy;
    $("#photo-button").disabled = busy;
    $("#audio-button").disabled = busy;
    $("#record-button").disabled = busy;
    $("#stop-recording-button").disabled = busy;
    messagesRoot.querySelectorAll("button[data-action]").forEach((button) => { button.disabled = busy; });
    messageInput.disabled = busy;
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (inFlight) return;
    const text = messageInput.value.trim();
    if (!text && !attachments.length) {
      setStatus("Escreva uma mensagem ou anexe uma foto/áudio.");
      messageInput.focus();
      return;
    }
    setBusy(true);
    try {
      const packed = await Promise.all(attachments.map(async ({ file }) => ({
        filename: file.name,
        mime_type: file.type,
        data: await readAsBase64(file),
      })));
      const result = await api("/api/chat", { text, attachments: packed });
      renderMessages(result.messages);
      messageInput.value = "";
      attachments.forEach((entry) => URL.revokeObjectURL(entry.url));
      attachments = [];
      updateAttachmentPreview();
      setStatus("Mensagem enviada.");
      messageInput.focus();
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function resolveProposal(action, pendingId) {
    if (inFlight) return;
    setBusy(true);
    try {
      const result = await api("/api/chat", { action, pending_id: pendingId });
      renderMessages(result.messages);
      setStatus(action === "confirm" ? "Registro confirmado." : "Proposta cancelada.");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStatus("Este navegador não oferece gravação de áudio. Você ainda pode anexar um arquivo de áudio.");
      return;
    }
    try {
      recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferred = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"];
      const mimeType = preferred.find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(recordingStream, mimeType ? { mimeType } : undefined);
      mediaRecorder = recorder;
      recordingChunks = [];
      recordingBytes = 0;
      recordingRejected = false;
      recorder.addEventListener("dataavailable", (event) => {
        if (!event.data.size || recordingRejected) return;
        if (recordingBytes + event.data.size > MAX_FILE_BYTES) {
          recordingRejected = true;
          recordingChunks = [];
          recordingBytes = 0;
          if (recorder.state !== "inactive") recorder.stop();
          setStatus("A gravação passou de 4 MB e foi descartada. Grave um áudio mais curto.");
          return;
        }
        recordingChunks.push(event.data);
        recordingBytes += event.data.size;
      });
      recorder.addEventListener("stop", () => {
        clearTimeout(recordingTimer);
        recordingTimer = null;
        if (!recordingRejected && recordingChunks.length) {
          const blob = new Blob(recordingChunks, { type: recorder.mimeType || "audio/webm" });
          const extension = blob.type.includes("ogg") ? "ogg" : "webm";
          const file = new File([blob], `gravacao-${Date.now()}.${extension}`, { type: blob.type });
          addFiles([file]);
        }
        recordingChunks = [];
        recordingBytes = 0;
        recordingStream?.getTracks().forEach((track) => track.stop());
        recordingStream = null;
        mediaRecorder = null;
        $("#record-button").hidden = false;
        $("#stop-recording-button").hidden = true;
        $("#recording-label").hidden = true;
      });
      recorder.start(1000);
      recordingTimer = setTimeout(() => {
        if (!mediaRecorder || mediaRecorder.state === "inactive") return;
        recordingRejected = true;
        recordingChunks = [];
        recordingBytes = 0;
        mediaRecorder.stop();
        setStatus("A gravação atingiu 2 minutos e foi descartada. Grave um áudio mais curto.");
      }, MAX_RECORDING_MS);
      $("#record-button").hidden = true;
      $("#stop-recording-button").hidden = false;
      $("#recording-label").hidden = false;
      setStatus("Gravando. Pare a gravação e envie o áudio pela conversa.");
    } catch {
      clearTimeout(recordingTimer);
      recordingTimer = null;
      recordingChunks = [];
      recordingBytes = 0;
      mediaRecorder = null;
      recordingStream?.getTracks().forEach((track) => track.stop());
      recordingStream = null;
      $("#record-button").hidden = false;
      $("#stop-recording-button").hidden = true;
      $("#recording-label").hidden = true;
      setStatus("Não consegui acessar o microfone. Verifique a permissão ou anexe um arquivo de áudio.");
    }
  }

  async function loadChat() {
    try {
      const [state, chat] = await Promise.all([api("/api/state"), api("/api/chat")]);
      $("#property-id").textContent = String(state.property_id || "Propriedade local");
      $("#actor-id").textContent = `Operador ${state.actor_id}`;
      renderMessages(chat.messages, true);
      setStatus("Conversa local pronta.");
    } catch (error) {
      setStatus(`Não consegui abrir a conversa local: ${error.message}`);
    }
  }

  composer.addEventListener("submit", sendMessage);
  messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      composer.requestSubmit();
    }
  });
  $("#photo-button").addEventListener("click", () => photoInput.click());
  $("#audio-button").addEventListener("click", () => audioInput.click());
  photoInput.addEventListener("change", () => { addFiles(photoInput.files); photoInput.value = ""; });
  audioInput.addEventListener("change", () => { addFiles(audioInput.files); audioInput.value = ""; });
  $("#record-button").addEventListener("click", startRecording);
  $("#stop-recording-button").addEventListener("click", () => mediaRecorder?.stop());
  attachmentPreview.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-attachment]");
    if (!button) return;
    const [removed] = attachments.splice(Number(button.dataset.removeAttachment), 1);
    if (removed) URL.revokeObjectURL(removed.url);
    updateAttachmentPreview();
  });
  messagesRoot.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action][data-pending-id]");
    if (button) resolveProposal(button.dataset.action, button.dataset.pendingId);
  });
  window.addEventListener("beforeunload", () => recordingStream?.getTracks().forEach((track) => track.stop()));
  loadChat();
})();
