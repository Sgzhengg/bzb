// Define an object to store extension state
let extensionState = {
  textareaFound: false,
  currentInteraction: "Idle",
  queuedMessages: [],
  lastMessageStatus: "No messages sent yet.",
};

let isPro = false;
let isAuthenticating = false; // Flag to prevent multiple authentications
let lastCheckTimestamp = 0;
let lastSuccessfulCheckTimestamp = 0; // New timestamp for successful checks
let backoffInterval = 5 * 60 * 1000; // Start with 5 minutes (in milliseconds)
let maxBackoffInterval = 4 * 60 * 60 * 1000; // Max backoff of 4 hours
let lastBackoffReset = 0;
let lastChatGPTPageLoadCheck = 0; // New timestamp for ChatGPT page loads

const DAILY_RESET = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
const MIN_FORCE_CHECK_INTERVAL = 2 * 60 * 1000; // 2 minutes — minimum between forced checks
const CHATGPT_CHECK_THRESHOLD = 30 * 60 * 1000; // 30 minutes threshold for ChatGPT page loads
const PRO_CACHE_DURATION = 12 * 60 * 60 * 1000; // 12 hours for pro users
const NON_PRO_CACHE_DURATION = 60 * 60 * 1000; // 1 hour for non-pro users

// Add this near the top of the file, with other initialization code
chrome.runtime.setUninstallURL("https://www.chataiqueue.com/goodbye", () => {
  if (chrome.runtime.lastError) {
    console.error("Error setting uninstall URL:", chrome.runtime.lastError);
  } else {
    console.log("Uninstall URL set successfully");
  }
});

function checkProStatus(forceCheck = false) {
  const currentTime = Date.now();

  // Reset backoff daily
  if (currentTime - lastBackoffReset >= DAILY_RESET) {
    backoffInterval = 5 * 60 * 1000; // Reset to 5 minutes
    lastBackoffReset = currentTime;
  }

  // Determine cache duration based on pro status
  const cacheDuration = isPro ? PRO_CACHE_DURATION : NON_PRO_CACHE_DURATION;
  
  // Check if we should make an API call based on the backoff interval or force check
  if (!forceCheck && isAuthenticating) {
    return; // Don't proceed if authentication is in progress
  }
  
  // Skip check if within cache duration and not forced
  if (!forceCheck && currentTime - lastSuccessfulCheckTimestamp < cacheDuration) {
    return;
  }
  
  // Skip check if within backoff interval and not forced
  if (!forceCheck && currentTime - lastCheckTimestamp < backoffInterval) {
    return;
  }

  // Even forced checks must respect a minimum interval (except sign-in/install which call checkSubscriptionStatus directly)
  if (forceCheck && currentTime - lastSuccessfulCheckTimestamp < MIN_FORCE_CHECK_INTERVAL) {
    return;
  }

  isAuthenticating = true;

  // First, check if we already have an email stored
  chrome.storage.local.get(["email"], function (data) {
    if (data.email) {
      // If we have an email, directly check the subscription
      checkSubscriptionStatus(data.email, forceCheck);
    } else {
      // If no email, proceed with authentication
      // Check if we're on Brave browser
      if (navigator.brave) {
        console.log("Brave browser detected, skipping this auth method token ");
        isAuthenticating = false;
        return;
      }

      chrome.identity.getAuthToken({ interactive: true }, function (token) {
        if (chrome.runtime.lastError) {
          console.error(
            "Error retrieving auth token:",
            chrome.runtime.lastError.message
          );
          isAuthenticating = false;
          return;
        }
        fetchUserInfoAndCheckSubscription(token, forceCheck);
      });
    }
  });
}

function checkSubscriptionStatus(email, forceCheck = false) {
  fetch(
    `https://chrome-extension-backend-rho.vercel.app/api/checkSub?email=${email}`
  )
    .then((response) => response.json())
    .then((data) => {
      isPro = data.hasBundle;
      lastCheckTimestamp = Date.now();
      lastSuccessfulCheckTimestamp = Date.now(); // Update successful check timestamp
      
      chrome.storage.local.set(
        {
          isPro,
          lastCheckTimestamp,
          lastSuccessfulCheckTimestamp,
          backoffInterval,
          lastBackoffReset,
        },
        () => {
          isAuthenticating = false;
          notifyProStatus();
          notifyPopupToRefresh();
          
          // Only increase backoff for regular checks, not forced ones
          if (!forceCheck) {
            backoffInterval = Math.min(backoffInterval * 2, maxBackoffInterval);
          }
        }
      );
    })
    .catch((error) => {
      console.error("Error checking subscription status:", error);
      isAuthenticating = false;
    });
}

function initiateSignIn() {
  console.log("Initiating sign in process...");
  chrome.identity.getAuthToken({ interactive: true }, function (token) {
    if (chrome.runtime.lastError) {
      console.error(
        "Error retrieving auth token:",
        chrome.runtime.lastError.message
      );
      console.log("Falling back to web auth flow authentication...");
      // Fall back to launchWebAuthFlow
      fallbackAuthentication();
    } else {
      console.log("Successfully retrieved auth token, fetching user info...");
      fetchUserInfoAndCheckSubscription(token, true); // Force check on sign-in
    }
  });
}

function fallbackAuthentication() {
  const clientId =
    "831569868315-1tcogogjpit7o3rbism5umqtiv14jfsg.apps.googleusercontent.com"; // Replace with your actual client ID
  const redirectUri = chrome.identity.getRedirectURL();
  const encodedRedirectUri = encodeURIComponent(redirectUri);

  console.log(
    redirectUri,
    encodedRedirectUri,
    "redirectUri",
    "encodedRedirectUri"
  );
  const authUrl = `https://accounts.google.com/o/oauth2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(
    redirectUri
  )}&response_type=token&scope=email%20profile`;

  chrome.identity.launchWebAuthFlow(
    { url: authUrl, interactive: true },
    function (responseUrl) {
      if (chrome.runtime.lastError) {
        console.error(
          "LaunchWebAuthFlow failed:",
          chrome.runtime.lastError.message
        );
        isAuthenticating = false;
        return;
      }

      const token = new URLSearchParams(new URL(responseUrl).hash.slice(1)).get(
        "access_token"
      );

      if (token) {
        // Use the token to fetch user info and continue with the existing flow
        fetchUserInfoAndCheckSubscription(token, true); // Force check on sign-in
      } else {
        console.error("Failed to get access token from auth response");
        isAuthenticating = false;
      }
    }
  );
}

function fetchUserInfoAndCheckSubscription(token, forceCheck = false) {
  fetch("https://www.googleapis.com/oauth2/v3/userinfo?alt=json", {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((response) => response.json())
    .then((userInfo) => {
      chrome.storage.local.set({ email: userInfo.email }, () => {
        checkSubscriptionStatus(userInfo.email, forceCheck);
      });
    })
    .catch((error) => {
      console.error("Error fetching user info:", error);
      isAuthenticating = false;
    });
}

function notifyPopupToRefresh() {
  chrome.runtime.sendMessage({ action: "refreshPopup" });
}

// Handle sign-out properly
function handleSignOut() {
  chrome.storage.local.remove(
    ["email", "isPro", "lastSuccessfulCheckTimestamp", "promptDelay", "hasRunContentScript"],
    () => {
      isPro = false;
      lastSuccessfulCheckTimestamp = 0;
      notifyProStatus();
      notifyPopupToRefresh();
    }
  );
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "openPopup") {
    chrome.action.openPopup();
  } else if (request.action === "checkProStatus") {
    // Use cache on popup open — only hit API if cache is expired
    checkProStatus(false);
    sendResponse({ success: true });
  } else if (request.action === "signOut") {
    handleSignOut();
    sendResponse({ success: true });
  }
  return true; // Keep the message channel open for async responses
});

function notifyProStatus() {
  chrome.tabs.query({}, function (tabs) {
    for (let tab of tabs) {
      chrome.tabs.sendMessage(
        tab.id,
        { type: "proStatus", isPro },
        (response) => {
          if (chrome.runtime.lastError) {
            console.log(
              "Error sending message to tab:",
              tab.id,
              chrome.runtime.lastError.message
            );
            // Don't throw an error, just log it
          }
        }
      );
    }
  });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "getProStatus") {
    // Force a check if it's been a while since the last successful check
    const currentTime = Date.now();
    const cacheDuration = isPro ? PRO_CACHE_DURATION : NON_PRO_CACHE_DURATION;
    
    if (currentTime - lastSuccessfulCheckTimestamp > cacheDuration) {
      checkProStatus(true); // Force a check if cache is expired
    }
    
    sendResponse({ isPro });
  }
  return true; // Keep the message channel open for async responses
});

chrome.runtime.onInstalled.addListener(() => {
  checkProStatus(true); // Force check on installation
  chrome.storage.local.get(["promptDelay"], function (result) {
    if (typeof result.promptDelay === "undefined") {
      chrome.storage.local.set({ promptDelay: 0 });
    }
  });
});

chrome.runtime.onStartup.addListener(() => {
  checkProStatus(true); // Force check on browser startup
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    const currentTime = Date.now();
    
    // Check if the URL is ChatGPT
    if (tab.url && tab.url.includes("chat.openai.com")) {
      // Only force check if it's been a while since the last ChatGPT page load check
      if (currentTime - lastChatGPTPageLoadCheck > CHATGPT_CHECK_THRESHOLD) {
        checkProStatus(true); // Force check when ChatGPT page loads
        lastChatGPTPageLoadCheck = currentTime;
      } else {
        // Regular check if within threshold
        checkProStatus(false);
      }
    }

    if (changeInfo.url && chrome.scripting) {
      chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ["content.js"],
      });
    }
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "openStripeCheckout") {
    console.log("Received openStripeCheckout message");
    chrome.storage.local.get(["email"], function (data) {
      console.log("Retrieved email from storage:", data.email);
      if (data.email) {
        console.log("Making checkout request with user email:", data.email);
        fetch(
          "https://chrome-extension-backend-rho.vercel.app/api/stripe/create-checkout",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ email: data.email }),
          }
        )
          .then((response) => {
            console.log("Received response from checkout endpoint");
            return response.json();
          })
          .then((data) => {
            if (data.url) {
              console.log("Opening checkout URL:", data.url);
              chrome.tabs.create({ url: data.url });
            } else {
              console.error("No checkout URL received from the server");
            }
          })
          .catch((error) => {
            console.error("Error creating checkout session:", error);
          });
      } else if (!data.email) {
        console.log("Making checkout request with default email");
        fetch(
          "https://chrome-extension-backend-rho.vercel.app/api/stripe/create-checkout",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ email: "" }),
          }
        )
          .then((response) => {
            console.log("Received response from checkout endpoint");
            return response.json();
          })
          .then((data) => {
            if (data.url) {
              console.log("Opening checkout URL:", data.url);
              chrome.tabs.create({ url: data.url });
            } else {
              console.error("No checkout URL received from the server");
            }
          })
          .catch((error) => {
            console.error("Error creating checkout session:", error);
          });
      } else {
        console.error("No email found in storage");
        // Optionally, you could trigger the authentication process here
      }
    });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "initiateSignIn") {
    console.log("Received initiateSignIn message");
    fallbackAuthentication();

    return true; // Indicates that the response will be sent asynchronously
  }
});
