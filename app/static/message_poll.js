(() => {
  "use strict";

  const conversation = document.getElementById("conversation");
  const status = document.getElementById("message-poll-status");
  if (!conversation || !status) {
    return;
  }

  const messageIds = Array.from(conversation.querySelectorAll("[data-message-id]"))
    .map((element) => Number(element.dataset.messageId))
    .filter(Number.isFinite);
  let lastMessageId = messageIds.length ? Math.max(...messageIds) : 0;

  const formatTimestamp = (value) => {
    const timestamp = new Date(value);
    if (Number.isNaN(timestamp.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(timestamp);
  };

  const appendMessage = (message) => {
    if (conversation.querySelector(`[data-message-id="${message.id}"]`)) {
      return;
    }
    document.getElementById("conversation-empty")?.remove();

    const bubble = document.createElement("article");
    bubble.className = `bubble ${message.is_mine ? "mine" : "theirs"}`;
    bubble.dataset.messageId = String(message.id);

    const sender = document.createElement("strong");
    sender.textContent = message.sender;
    const body = document.createElement("p");
    body.textContent = message.body;
    const time = document.createElement("time");
    time.textContent = formatTimestamp(message.created_at);

    bubble.append(sender, body, time);
    conversation.appendChild(bubble);
    lastMessageId = Math.max(lastMessageId, Number(message.id));
  };

  const poll = async () => {
    try {
      const url = new URL(conversation.dataset.updatesUrl, window.location.origin);
      url.searchParams.set("after", String(lastMessageId));
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) {
        throw new Error("message polling failed");
      }
      const payload = await response.json();
      payload.messages.forEach(appendMessage);
      status.textContent = "새 메시지를 자동으로 확인합니다.";
      status.classList.remove("error");
    } catch (_error) {
      status.textContent = "새 메시지를 확인하지 못했습니다. 잠시 후 다시 시도합니다.";
      status.classList.add("error");
    } finally {
      window.setTimeout(poll, document.hidden ? 15000 : 4000);
    }
  };

  window.setTimeout(poll, 1000);
})();
