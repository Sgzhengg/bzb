// Define a queue to store messages
let messageQueue = [];
let sendingInProgress = false;
let userInput = "";
let isPro = false;
let currentURL = window.location.href;
let proStatusRequested = false;
const listenerMap = new WeakMap();
let userTyping = false;
let currentTypedMessage = "";
let lastMessageTime = 0;
let countdownInterval = null;
let editingInProgress = false;
let lastProStatusCheck = 0;
const PRO_STATUS_CHECK_INTERVAL = 5 * 60 * 1000; // Check every 5 minutes

// Add this utility function near the top of the file
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getHiddenTextarea() {
  const div = document.querySelector("div#prompt-textarea");
  if (!div) return null;
  let sibling = div.previousElementSibling;
  while (sibling) {
    if (sibling.tagName === "TEXTAREA") return sibling;
    sibling = sibling.previousElementSibling;
  }
  const parent = div.parentElement;
  if (parent) {
    const ta = parent.querySelector("textarea");
    if (ta) return ta;
  }
  return null;
}

function setProseMirrorContent(div, text) {
  div.focus();
  document.execCommand("selectAll");
  document.execCommand("delete");
  const lines = text.split("\n");
  for (let idx = 0; idx < lines.length; idx++) {
    if (idx > 0) document.execCommand("insertParagraph");
    if (lines[idx].length > 0)
      document.execCommand("insertText", false, lines[idx]);
  }
}

// Initialize pro status from storage
chrome.storage.local.get(["isPro"], function (result) {
  isPro = result.isPro || false;
  requestProStatus(); // Request fresh status on load
});

// Request pro status from background script
function requestProStatus() {
  const currentTime = Date.now();
  
  // Only request if we haven't checked recently or never checked
  if (currentTime - lastProStatusCheck > PRO_STATUS_CHECK_INTERVAL || lastProStatusCheck === 0) {
    lastProStatusCheck = currentTime;
    
    chrome.runtime.sendMessage({ type: "getProStatus" }, (response) => {
      if (chrome.runtime.lastError) {
        console.log(
          "Error getting pro status:",
          chrome.runtime.lastError.message
        );
        // Retry after a short delay
        setTimeout(requestProStatus, 1000);
      } else if (response) {
        // Handle the pro status
        handleProStatus(response.isPro);
      }
    });
  }
}

// Handle pro status updates
function handleProStatus(newProStatus) {
  // Only update if the status has changed
  if (isPro !== newProStatus) {
    console.log("Pro status changed:", newProStatus);
    isPro = newProStatus;
    
    // Update storage
    chrome.storage.local.set({ isPro: newProStatus });
    
    // Update UI elements that depend on pro status
    updateQueueIndicator();
    updateMessageList();
    
    // Check queue limits
    checkQueueLimit();
  }
}

// Add this near the top of the file
// Listen for pro status updates from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "proStatus") {
    handleProStatus(request.isPro);
    sendResponse({ success: true });
  }
  return true;
});

// Check if we're on ChatGPT and request pro status
if (window.location.href.includes("chat.openai.com")) {
  requestProStatus();
}

function checkQueueLimit() {
  if (!isPro && messageQueue.length >= 3) {
    showQueueLimitAlert();
    return false;
  }
  return true;
}

function setUniqueEventListener(element, eventType, listener, options) {
  if (!listenerMap.has(element)) {
    listenerMap.set(element, new Map());
  }

  const elementListeners = listenerMap.get(element);

  if (!elementListeners.has(eventType)) {
    element.addEventListener(eventType, listener, options);
    elementListeners.set(eventType, listener);
  }
}

async function attemptToSendMessage(message) {
  const inputDiv = document.querySelector("div#prompt-textarea");

  console.log("Attempting to send message:", message);

  if (sendingInProgress) {
    console.log("Sending already in progress, aborting");
    return false;
  }
  await new Promise((resolve) => setTimeout(resolve, 200));

  const continueButton = Array.from(
    document.querySelectorAll("button.btn")
  ).find((btn) => btn.textContent.includes("Continue generating"));

  if (continueButton) {
    continueButton.click();
    console.log("Continue button found, clicking");
    await new Promise((resolve) => setTimeout(resolve, 1000));
    sendingInProgress = false;
    return;
  }

  if (inputDiv.innerText.trim().length && messageQueue.length > 0) {
    console.log("User is still typing, aborting");
    userTyping = true;
    updateMessageList(); // Update to show "waiting for user" message
    return false;
  }

  userTyping = false;
  sendingInProgress = true;

  try {
    const loading =
      document.querySelector('button[data-testid="stop-button"]') ||
      document.querySelector('button[aria-label="Stop generating"]') ||
      document.querySelector('button[data-testid="fruitjuice-stop-button"]') ||
      document.querySelector('button[aria-label="Stop streaming"]');

    console.log("Loading state:", loading ? "active" : "inactive");

    if (!loading && inputDiv) {
      console.log("Setting message in input div");
      const hiddenTA = getHiddenTextarea();
      if (hiddenTA) {
        hiddenTA.value = message;
        hiddenTA.dispatchEvent(new InputEvent("input", { bubbles: true }));
      }
      setProseMirrorContent(inputDiv, message);
      await new Promise((resolve) => setTimeout(resolve, 100));
      inputDiv.dispatchEvent(
        new InputEvent("input", { bubbles: true, cancelable: true })
      );

      console.log("Looking for send button");
      const button =
        document.querySelector('button[data-testid="send-button"]') ||
        document.querySelector('button[aria-label="Send message"]') ||
        document.querySelector(
          'button[data-testid="fruitjuice-send-button"]'
        ) ||
        document.querySelector('button[aria-label="Send prompt"]');

      if (button) {
        button.disabled = false;
        button.dispatchEvent(
          new Event("click", {
            bubbles: true,
            cancelable: true,
          })
        );

        console.log("Send button found, clicking", button);
        return true;
      } else {
        console.log("Send button not found");
        return false;
      }
    } else {
      console.log("Loading active or input div not found");
      return false;
    }
  } catch (error) {
    console.error("Error during message sending:", error);
    return false;
  } finally {
    sendingInProgress = false;
    console.log("Sending process completed");
  }
}

function showQueueLimitAlert() {
  const alertDiv = document.createElement("div");
  alertDiv.id = "queue-limit-alert";
  alertDiv.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;
  const modalContent = document.createElement("div");
  modalContent.style.cssText = `
    background-color: #f8f9fa;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    width: 340px;
    text-align: center;
    color: #333;
    font-family: Arial, sans-serif;
  `;
  const alertContent = `
    <p style="color: #666; margin-bottom: 15px;">You've reached your limit of 1 message in the queue.</p>
    <h2 style="color: #4a4a4a; margin-bottom: 20px; font-size: 24px;">🚀 Upgrade to ChatGPT Queue Pro</h2>
    <ul style="text-align: left; padding-left: 20px; margin-bottom: 20px;">
      <li style="margin-bottom: 10px;">🕒 <strong>Save Time:</strong> Queue your questions and keep your flow going.</li>
      <li style="margin-bottom: 10px;">🚀 <strong>Efficiency at Its Best:</strong> Become a pro with bulk prompting and unlimited queues.</li>
      <li style="margin-bottom: 10px;">🎯 <strong>One Time Investment:</strong> 100% money back guarantee.</li>
    </ul>
    <p style="color: #666; margin-bottom: 20px; font-style: italic;">"It's a sweet little extension! I tried it once and bought it immediately. I can't stop thinking of things I want to do with it" -<a href="https://www.reddit.com/r/ChatGPTPro/comments/1ermx8d/comment/li5llj5/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button" target="_blank" style="color: #666; text-decoration: underline;">DrivewayGrappler</a>
(August 14, 2024)</p>
    <button id="go-pro-button" style="background-color: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 25px; cursor: pointer; font-size: 16px; font-weight: bold; transition: background-color 0.3s;">Boost Your Productivity Now</button>
  `;
  modalContent.innerHTML = alertContent;
  alertDiv.appendChild(modalContent);
  document.body.appendChild(alertDiv);

  alertDiv.addEventListener("click", (event) => {
    if (event.target === alertDiv) {
      document.body.removeChild(alertDiv);
    }
  });

  const goProButton = modalContent.querySelector("#go-pro-button");
  goProButton.addEventListener("mouseenter", () => {
    goProButton.style.backgroundColor = "#45a049";
  });
  goProButton.addEventListener("mouseleave", () => {
    goProButton.style.backgroundColor = "#4CAF50";
  });
  goProButton.addEventListener("click", () => {
    document.body.removeChild(alertDiv);
    chrome.runtime.sendMessage({ action: "openStripeCheckout" });
  });
}

// async function processMessageQueue() {
//   console.log("Processing message queue");
//   if (sendingInProgress || messageQueue.length === 0) {
//     console.log(
//       "Queue processing aborted: ",
//       sendingInProgress ? "Sending in progress" : "Queue is empty"
//     );
//     return;
//   }
//   const message = messageQueue[0];
//   console.log("Attempting to send message from queue:", message);

//   const success = await attemptToSendMessage(message);

//   if (success) {
//     console.log("Message sent successfully, removing from queue");
//     messageQueue.shift();
//     chrome.storage.local.set({ queuedMessages: messageQueue });
//   } else {
//     console.log("Failed to send message, keeping in queue");
//   }

//   updateQueueIndicator();
//   updateMessageList();
// }

function updateQueueIndicator() {
  let queueIndicator = document.querySelector("#queue-indicator");
  const inputDiv = document.querySelector(
    "div#prompt-textarea[contenteditable='true']"
  );
  if (!queueIndicator) {
    queueIndicator = document.createElement("span");
    queueIndicator.id = "queue-indicator";
    queueIndicator.style.cssText =
      "position: absolute; z-index: 999; top: 0; right: 30px; background-color: red; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px;";
    inputDiv.parentNode.insertBefore(queueIndicator, inputDiv.nextSibling);
  }
  queueIndicator.textContent = messageQueue.length.toString();
  queueIndicator.style.display = messageQueue.length > 0 ? "flex" : "none";
}

function updateMessageList(remainingDelay = 0) {
  // Don't re-render while the user is editing a queue item
  if (editingInProgress) return;

  let messageList = document.querySelector("#message-list");

  // If there are no messages and no delay, clear any existing countdown
  if (messageQueue.length === 0 && remainingDelay === 0) {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
    if (messageList) {
      messageList.style.display = "none";
    }
    return;
  }

  if (!messageList) {
    messageList = document.createElement("div");
    messageList.id = "message-list";
    messageList.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 250px;
      max-height: 300px;
      background-color: white;
      border: 1px solid #ccc;
      border-radius: 8px;
      color: black;
      padding: 10px;
      overflow-y: auto;
      z-index: 1000;
      display: none;
    `;
    document.body.appendChild(messageList);

    const style = document.createElement("style");
    style.textContent = `
      @media (prefers-color-scheme: dark) {
        #message-list {
          background-color: rgba(0, 0, 0, 0.9);
          color: #fff;
          border-color: #666;
        }
        #message-list li {
          border-bottom-color: #555;
        }
        #message-list .queue-edit-input {
          background-color: #333;
          color: #fff;
          border-color: #666;
        }
      }
      #message-list .queue-btn:hover {
        opacity: 0.7;
      }
    `;
    document.head.appendChild(style);
  }

  messageList.style.display = "block";
  let content = '<ul style="list-style: none; padding: 0; margin: 0;">';

  content += messageQueue
    .map(
      (msg, index) =>
        `<li style="margin-bottom: 8px; padding: 5px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 6px;" data-index="${index}">
          <span class="queue-msg-text" style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(msg)}</span>
          <button class="queue-btn queue-edit-btn" data-index="${index}" title="Edit" style="background: none; border: none; cursor: pointer; font-size: 14px; padding: 2px 4px; color: inherit;">✎</button>
          <button class="queue-btn queue-delete-btn" data-index="${index}" title="Delete" style="background: none; border: none; cursor: pointer; font-size: 14px; padding: 2px 4px; color: #e74c3c;">✕</button>
        </li>`
    )
    .join("");

  if (userTyping) {
    content += `<li style="font-size: 12px; margin-top: 8px; padding: 5px; font-style: italic; color: #888;">Waiting for user to finish typing...</li>`;
  }

  if (remainingDelay > 0) {
    const secondsRemaining = Math.ceil(remainingDelay / 1000);
    content += `<li style="font-size: 12px; margin-top: 8px; padding: 5px; font-style: italic; color: #888;">Waiting ${secondsRemaining}s before next message...</li>`;
  }

  content += "</ul>";
  messageList.innerHTML = content;

  // Attach delete button handlers
  messageList.querySelectorAll(".queue-delete-btn").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const index = parseInt(btn.getAttribute("data-index"));
      deleteQueueItem(index);
    });
  });

  // Attach edit button handlers
  messageList.querySelectorAll(".queue-edit-btn").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const index = parseInt(btn.getAttribute("data-index"));
      startEditQueueItem(index);
    });
  });
}

function startEditQueueItem(index) {
  if (index < 0 || index >= messageQueue.length) return;

  const messageList = document.querySelector("#message-list");
  if (!messageList) return;

  const li = messageList.querySelector(`li[data-index="${index}"]`);
  if (!li) return;

  const currentMsg = messageQueue[index];
  editingInProgress = true;

  // Replace li contents with an input and save button
  li.innerHTML = `
    <input class="queue-edit-input" type="text" value="${escapeHtml(currentMsg)}" style="flex: 1; padding: 3px 5px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; background: inherit; color: inherit;">
    <button class="queue-btn queue-save-btn" title="Save" style="background: none; border: none; cursor: pointer; font-size: 14px; padding: 2px 4px; color: #27ae60;">✓</button>
    <button class="queue-btn queue-delete-btn" data-index="${index}" title="Delete" style="background: none; border: none; cursor: pointer; font-size: 14px; padding: 2px 4px; color: #e74c3c;">✕</button>
  `;

  const input = li.querySelector(".queue-edit-input");
  const saveBtn = li.querySelector(".queue-save-btn");
  const deleteBtn = li.querySelector(".queue-delete-btn");

  input.focus();
  input.select();

  function saveEdit() {
    const newValue = input.value.trim();
    if (newValue && newValue !== currentMsg) {
      messageQueue[index] = newValue;
    }
    editingInProgress = false;
    updateMessageList();
  }

  function cancelEdit() {
    editingInProgress = false;
    updateMessageList();
  }

  saveBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    saveEdit();
  });

  deleteBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    editingInProgress = false;
    deleteQueueItem(index);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      saveEdit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      cancelEdit();
    }
  });

  // Prevent keydown from propagating to ChatGPT's input handler
  input.addEventListener("keydown", (e) => {
    e.stopPropagation();
  }, { capture: true });

  // Cancel edit if the input loses focus (e.g. user clicks elsewhere)
  input.addEventListener("blur", () => {
    // Short delay so that clicks on save/delete buttons register before blur fires
    setTimeout(() => {
      if (editingInProgress) {
        cancelEdit();
      }
    }, 150);
  });
}

function deleteQueueItem(index) {
  if (index < 0 || index >= messageQueue.length) return;
  messageQueue.splice(index, 1);
  updateQueueIndicator();
  updateMessageList();
}

function handleKeyDown(event) {
  const sendButton =
    document.querySelector('button[data-testid="send-button"]') ||
    document.querySelector('button[aria-label="Send message"]') ||
    document.querySelector('button[data-testid="fruitjuice-send-button"]') ||
    document.querySelector('button[aria-label="Send prompt"]');

  const loading =
    document.querySelector('button[data-testid="stop-button"]') ||
    document.querySelector('button[aria-label="Stop generating"]') ||
    document.querySelector('button[data-testid="fruitjuice-stop-button"]') ||
    document.querySelector('button[aria-label="Stop streaming"]');

  const inputDiv = document.querySelector("div#prompt-textarea");
  const currentInputValue = inputDiv ? inputDiv.innerText.trim() : "";

  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    event.stopPropagation();

    // Store the raw message without any escaping
    if (currentInputValue !== currentTypedMessage) {
      currentTypedMessage = currentInputValue;
    }

    if (messageQueue.length === 0 && !loading && currentTypedMessage) {
      attemptToSendMessage(currentTypedMessage);
      return;
    }

    if (currentTypedMessage && (isPro || checkQueueLimit())) {
      // Store the raw message in the queue
      messageQueue.push(currentTypedMessage);

      if (inputDiv) {
        setProseMirrorContent(inputDiv, "");
        inputDiv.dispatchEvent(new InputEvent("input", { bubbles: true }));
      }
      currentTypedMessage = "";
      console.log("Message queued:", currentTypedMessage);
      updateQueueIndicator();
      updateMessageList();
      processMessageQueue();
    } else {
      console.log(
        "Message not queued:",
        currentTypedMessage,
        "Pro status:",
        isPro,
        "Queue length:",
        messageQueue.length,
        "Send button:",
        sendButton,
        "Loading:",
        loading
      );
    }
  }
}

function reinjectUIComponents() {
  editingInProgress = false;

  const inputDiv = document.querySelector(
    "div#prompt-textarea[contenteditable='true']"
  );

  if (inputDiv) {
    inputDiv.removeEventListener("keydown", handleKeyDown);
    inputDiv.removeEventListener("input", handleInput);
    inputDiv.hasListener = false;
    addEventListeners();
  }
}

function addEventListeners() {
  const inputDiv = document.querySelector(
    "div#prompt-textarea[contenteditable='true']"
  );

  if (inputDiv) {
    if (!inputDiv.hasListener) {
      inputDiv.addEventListener("keydown", handleKeyDown, {
        capture: true,
        passive: false,
      });
      inputDiv.addEventListener("input", handleInput);
      inputDiv.hasListener = true;
    }
  }
}

function handleInput(event) {
  currentTypedMessage = event.target.innerText;
}

function scheduleQueueProcessing() {
  setTimeout(async () => {
    if (!sendingInProgress && messageQueue.length > 0) {
      await processMessageQueue();
    }
    scheduleQueueProcessing();
  }, 1000);
}
setInterval(() => {
  if (window.location.href !== currentURL) {
    currentURL = window.location.href;
    reinjectUIComponents();
  }

  const inputDiv = document.querySelector(
    "div#prompt-textarea[contenteditable='true']"
  );
  if (inputDiv) {
    if (inputDiv.innerText !== userInput) {
      userInput = inputDiv.innerText;
      reinjectUIComponents();
    }
  }
}, 2000);

(function injectUI(retryCount = 0) {
  function handleInjection(inputDiv) {
    inputDiv.addEventListener("keydown", handleKeyDown, {
      capture: true,
      passive: false,
    });
    inputDiv.addEventListener("input", handleInput);
    inputDiv.hasListener = true;
    scheduleQueueProcessing();
    requestProStatus();
    setupContinueButtonWatcher();
  }

  let inputDiv = document.querySelector(
    "div#prompt-textarea[contenteditable='true']"
  );
  if (inputDiv) {
    handleInjection(inputDiv);
  } else {
    const observer = new MutationObserver((mutations, obs) => {
      inputDiv = document.querySelector(
        "div#prompt-textarea[contenteditable='true']"
      );
      if (inputDiv) {
        handleInjection(inputDiv);
        obs.disconnect();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    if (retryCount < 50) {
      setTimeout(() => injectUI(retryCount + 1), 500);
    }
  }
})();

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "addToQueue") {
    try {
      if (!request.messages || !Array.isArray(request.messages)) {
        console.error("Invalid messages array in addToQueue request");
        sendResponse({ success: false, error: "Invalid messages array" });
        return true;
      }

      if (!isPro && messageQueue.length + request.messages.length > 1) {
        showQueueLimitAlert();
        // Only add messages up to the limit
        const availableSlots = Math.max(0, 1 - messageQueue.length);
        messageQueue.push(...request.messages.slice(0, availableSlots));
      } else {
        messageQueue.push(...request.messages);
      }

      updateQueueIndicator();
      updateMessageList();
      processMessageQueue();
      sendResponse({ success: true });
    } catch (error) {
      console.error("Error in addToQueue handler:", error);
      sendResponse({ success: false, error: error.message });
    }
  }
  return true;
});

async function processMessageQueue() {
  if (editingInProgress || sendingInProgress || messageQueue.length === 0) return;

  if (!isPro && messageQueue.length > 1) {
    showQueueLimitAlert();
    // Remove extra messages beyond the limit
    messageQueue = messageQueue.slice(0, 1);
    updateQueueIndicator();
    updateMessageList();
    return;
  }

  const inputDiv = document.querySelector(
    "div#prompt-textarea[contenteditable='true']"
  );
  if (inputDiv && inputDiv.innerText.trim().length > 0) {
    userTyping = true;
    updateMessageList();
    return;
  }

  // Check if we need to wait due to delay
  const now = Date.now();
  const result = await chrome.storage.local.get(["promptDelay"]);
  const promptDelay = result.promptDelay || 0;
  const timeToWait = Math.max(0, lastMessageTime + promptDelay - now);

  if (timeToWait > 0) {
    // Clear any existing countdown
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }

    // Start a new countdown
    let remainingTime = timeToWait;
    updateMessageList(remainingTime);

    countdownInterval = setInterval(() => {
      remainingTime = Math.max(0, remainingTime - 1000);
      updateMessageList(remainingTime);

      if (remainingTime <= 0) {
        clearInterval(countdownInterval);
        countdownInterval = null;
      }
    }, 1000);

    await new Promise((resolve) => setTimeout(resolve, timeToWait));
  }

  userTyping = false;
  const message = messageQueue[0];
  const success = await attemptToSendMessage(message);

  if (success) {
    lastMessageTime = Date.now();
    messageQueue.shift();
  }

  updateQueueIndicator();
  updateMessageList();
}

function setupContinueButtonWatcher() {
  let lastClickTime = 0;
  const CLICK_COOLDOWN = 2000; // 2 seconds cooldown between clicks

  const observer = new MutationObserver((mutations) => {
    const now = Date.now();
    if (now - lastClickTime < CLICK_COOLDOWN) {
      return; // Skip if we're still in cooldown
    }

    const continueButton = Array.from(
      document.querySelectorAll("button.btn")
    ).find((btn) => btn.textContent.includes("Continue generating"));

    if (continueButton) {
      console.log("Continue button found, clicking automatically");
      continueButton.click();
      lastClickTime = now;
    }
  });

  // Reduce the scope of what we're observing and optimize the configuration
  const chatArea = document.querySelector("main") || document.body;
  observer.observe(chatArea, {
    childList: true,
    subtree: true,
    attributes: false, // We don't need attribute changes
    characterData: false, // We don't need text changes
  });

  return observer;
}
