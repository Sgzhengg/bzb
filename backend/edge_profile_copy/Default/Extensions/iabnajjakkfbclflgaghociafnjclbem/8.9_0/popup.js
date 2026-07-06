document.addEventListener("DOMContentLoaded", function () {
  // Force a pro status check when popup is opened
  chrome.runtime.sendMessage({ action: "checkProStatus" });
  
  chrome.storage.local.get(["email", "isPro"], function (data) {
    const userEmail = document.getElementById("userEmail");
    const proStatus = document.getElementById("proStatus");
    const promptChainLink = document.getElementById("promptChainLink");
    const bulkInputContainer = document.getElementById("bulkInputContainer");
    const queueButton = document.getElementById("queueButton");
    const bulkQueueInput = document.getElementById("bulkQueueInput");
    const signOutButton = document.getElementById("signOutButton");
    const promptDelayInput = document.getElementById("promptDelay");
    const delaySettingsLink = document.getElementById("delaySettingsLink");
    const delaySettingsContainer = document.getElementById(
      "delaySettingsContainer"
    );

    function updateUIVisibility(isSignedIn) {
      const proFeatures = document.getElementById("pro-features");

      if (isSignedIn) {
        proStatus.style.display = "block";
        signOutButton.classList.remove("hidden");
        proFeatures.classList.remove("hidden");
      } else {
        proStatus.style.display = "none";
        signOutButton.classList.add("hidden");
        proFeatures.classList.add("hidden");
        bulkInputContainer.style.display = "none";
        delaySettingsContainer.style.display = "none";
      }
    }

    function refreshUI() {
      chrome.storage.local.get(["email", "isPro"], function (data) {
        if (data.email) {
          userEmail.textContent = `Signed in as: ${data.email}`;
          updateUIVisibility(true);
        } else {
          userEmail.innerHTML =
            '<a href="#" class="button"><i class="fab fa-google"></i> Sign in with Google</a>';
          updateUIVisibility(false);
          userEmail.querySelector("a").addEventListener("click", function (e) {
            e.preventDefault();
            chrome.runtime.sendMessage(
              { action: "initiateSignIn" },
              function (response) {
                if (chrome.runtime.lastError) {
                  console.error(
                    "Error initiating sign-in:",
                    chrome.runtime.lastError.message
                  );
                } else if (response && response.success) {
                  console.log("Sign-in process initiated");
                  userEmail.textContent = "Signing in...";
                }
              }
            );
          });
        }

        if (data.isPro) {
          proStatus.innerHTML = '<span class="pro-badge">PRO User</span>';
        } else {
          proStatus.innerHTML =
            '<a href="#" class="button">✨ Go Pro, Unlock Unlimited Queues and Bulk Prompting</a>';
          proStatus.querySelector("a").addEventListener("click", function (e) {
            e.preventDefault();
            chrome.runtime.sendMessage({ action: "openStripeCheckout" });
          });
        }

        updateProFeatures(data.isPro);
      });
    }

    chrome.runtime.onMessage.addListener(function (
      request,
      sender,
      sendResponse
    ) {
      if (request.action === "refreshPopup") {
        refreshUI();
      }
    });

    refreshUI();

    function updateProFeatures(isPro) {
      if (isPro) {
        promptChainLink.classList.remove("pro-feature");
        promptChainLink.removeAttribute("title");
        bulkQueueInput.disabled = false;
        queueButton.disabled = false;
        delaySettingsLink.classList.remove("pro-feature");
        delaySettingsLink.removeAttribute("title");
        promptDelayInput.disabled = false;
      } else {
        promptChainLink.classList.add("pro-feature");
        promptChainLink.setAttribute(
          "title",
          "Upgrade to Pro to use this feature"
        );
        bulkQueueInput.disabled = true;
        queueButton.disabled = true;
        delaySettingsLink.classList.add("pro-feature");
        delaySettingsLink.setAttribute(
          "title",
          "Upgrade to Pro to use this feature"
        );
        promptDelayInput.disabled = true;
      }
    }

    promptChainLink.addEventListener("click", function () {
      // Get the current pro status from storage instead of using the stale data variable
      chrome.storage.local.get(["isPro"], function(result) {
        if (result.isPro) {
          bulkInputContainer.style.display =
            bulkInputContainer.style.display === "none" ? "block" : "none";
          if (bulkInputContainer.style.display === "block") {
            bulkQueueInput.focus();
          }
        }
      });
    });

    queueButton.addEventListener("click", function () {
      // Get the current pro status from storage
      chrome.storage.local.get(["isPro"], function(result) {
        if (!result.isPro) return;

        const messages = bulkQueueInput.value
          .split("~")
          .map((msg) => msg.trim())
          .filter((msg) => msg !== "");

        if (messages.length > 0) {
          chrome.tabs.query(
            { active: true, currentWindow: true },
            function (tabs) {
              if (!tabs[0]) return;
              chrome.tabs.sendMessage(
                tabs[0].id,
                { action: "addToQueue", messages: messages },
                function (response) {
                  if (chrome.runtime.lastError) {
                    console.error(
                      "Error sending message:",
                      chrome.runtime.lastError.message
                    );
                  } else if (response && response.success) {
                    console.log("Queue updated successfully");
                    bulkQueueInput.value = "";
                    bulkQueueInput.style.height = "40px";
                  }
                }
              );
            }
          );
        } else {
          console.log("No valid messages to queue");
        }
      });
    });

    bulkQueueInput.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = this.scrollHeight + "px";
    });

    signOutButton.addEventListener("click", function () {
      // Use the new signOut action in background.js
      chrome.runtime.sendMessage({ action: "signOut" }, function(response) {
        if (chrome.runtime.lastError) {
          console.error("Error signing out:", chrome.runtime.lastError.message);
        } else if (response && response.success) {
          console.log("Sign-out successful");
          // Clear local UI state
          messageQueue = [];
          refreshUI();
          promptDelayInput.value = "0";
          bulkQueueInput.value = "";
        }
      });
    });

    // Load saved delay
    chrome.storage.local.get(["promptDelay"], function (result) {
      promptDelayInput.value = "0"; // Always set to 0 by default
      if (result.promptDelay) {
        promptDelayInput.value = (result.promptDelay || 0) / 1000;
      }
    });

    // Save delay when changed
    promptDelayInput.addEventListener("change", () => {
      // Get the current pro status from storage
      chrome.storage.local.get(["isPro"], function(result) {
        if (result.isPro) {
          const delaySeconds = Math.max(0, parseInt(promptDelayInput.value) || 0);
          const delayMs = delaySeconds * 1000;
          chrome.storage.local.set({ promptDelay: delayMs });
        } else {
          promptDelayInput.value = "0"; // Reset to 0 if not pro
        }
      });
    });

    delaySettingsLink.addEventListener("click", function () {
      // Get the current pro status from storage instead of using the stale data variable
      chrome.storage.local.get(["isPro"], function(result) {
        if (result.isPro) {
          delaySettingsContainer.style.display =
            delaySettingsContainer.style.display === "none" ? "block" : "none";
          if (delaySettingsContainer.style.display === "block") {
            promptDelayInput.focus();
          }
        }
      });
    });
  });
});
