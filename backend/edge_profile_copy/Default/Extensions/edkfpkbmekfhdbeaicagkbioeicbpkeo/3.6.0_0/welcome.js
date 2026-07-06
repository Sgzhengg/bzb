// Welcome page functionality
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🎉 Welcome page loaded');
    
    // Initialize I18n Manager
    if (window.I18nManager) {
        await window.I18nManager.init();
        window.I18nManager.localizeDOM();
        console.log('🌐 I18nManager initialized on welcome page');
    }
    
    // Get extension info
    const manifest = chrome.runtime.getManifest();
    const currentVersion = manifest.version;
    
    // Update version display
    document.getElementById('currentVersion').textContent = `v${currentVersion}`;
    
    // Check if this is first install or update
    const installInfo = await getInstallInfo();
    await setupWelcomePage(installInfo);
    
    // Load changelog
    await loadChangelog(currentVersion);
    
    // Setup event listeners
    setupEventListeners();
    
    // Listen for language changes
    chrome.storage.onChanged.addListener((changes, namespace) => {
        if (namespace === 'local' && changes.language) {
            console.log('🌐 Language changed, re-localizing welcome page');
            // Re-initialize I18n and re-localize
            if (window.I18nManager) {
                window.I18nManager.init().then(() => {
                    window.I18nManager.localizeDOM();
                });
            }
        }
    });
});

async function getInstallInfo() {
    try {
        // Check stored version info
        const result = await chrome.storage.local.get(['lastSeenVersion', 'installDate']);
        const lastSeenVersion = result.lastSeenVersion;
        const installDate = result.installDate;
        
        const manifest = chrome.runtime.getManifest();
        const currentVersion = manifest.version;
        
        // Determine install type
        let installType = 'update';
        if (!lastSeenVersion) {
            installType = 'install';
            // Store install date
            await chrome.storage.local.set({
                installDate: Date.now(),
                lastSeenVersion: currentVersion
            });
        } else if (lastSeenVersion !== currentVersion) {
            installType = 'update';
            // Update last seen version
            await chrome.storage.local.set({
                lastSeenVersion: currentVersion
            });
        }
        
        return {
            type: installType,
            currentVersion,
            lastSeenVersion,
            installDate: installDate || Date.now()
        };
    } catch (error) {
        console.error('❌ Failed to get install info:', error);
        return {
            type: 'install',
            currentVersion: chrome.runtime.getManifest().version,
            lastSeenVersion: null,
            installDate: Date.now()
        };
    }
}

async function setupWelcomePage(installInfo) {
    const welcomeTitle = document.getElementById('welcomeTitle');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const tutorialVideo = document.getElementById('tutorialVideo');
    const featuresOverview = document.getElementById('featuresOverview');
    
    // Get localized text
    const getLocalizedText = async (key, fallback) => {
        if (window.I18nManager) {
            return window.I18nManager.getMessage(key) || fallback;
        }
        return fallback;
    };
    
    if (installInfo.type === 'install') {
        // First install - use localized text
        const welcomeTitleText = await getLocalizedText('welcome_title', '🎉 Welcome to N8N Master!');
        const welcomeMessageText = await getLocalizedText('welcome_message', 'Thank you for installing N8N Master. Here are the key features:');
        
        welcomeTitle.textContent = welcomeTitleText;
        welcomeMessage.textContent = welcomeMessageText;
        tutorialVideo.style.display = 'block';
        featuresOverview.style.display = 'block';
    } else {
        // Update - use localized text
        const welcomeTitleText = await getLocalizedText('welcome_title', '🎉 Welcome to N8N Master!');
        const welcomeMessageText = await getLocalizedText('welcome_message', `N8N Master has been updated to v${installInfo.currentVersion}. Here's what's new:`);
        
        welcomeTitle.textContent = '✨ N8N Master Updated!';
        welcomeMessage.textContent = welcomeMessageText;
        tutorialVideo.style.display = 'none';
        featuresOverview.style.display = 'none';
    }
    
    // Update date with localized format
    const updateDate = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    document.getElementById('updateDate').textContent = `Updated: ${updateDate}`;
    
    // Re-localize the DOM after content changes
    if (window.I18nManager) {
        window.I18nManager.localizeDOM();
    }
}

async function loadChangelog(currentVersion) {
    try {
        // Try to fetch changelog from CHANGELOG.md
        const changelogContent = document.getElementById('changelogContent');
        
        // Get all changelog data
        const allChangelogs = await getAllChangelogData();
        
        if (allChangelogs && Object.keys(allChangelogs).length > 0) {
            changelogContent.innerHTML = formatAllChangelogs(allChangelogs, currentVersion);
        } else {
            changelogContent.innerHTML = '<p>No changelog available.</p>';
        }
    } catch (error) {
        console.error('❌ Failed to load changelog:', error);
        document.getElementById('changelogContent').innerHTML = 
            '<p>Failed to load changelog. Please check the extension popup for latest updates.</p>';
    }
}

async function getAllChangelogData() {
    // This would ideally parse CHANGELOG.md
    // For now, return all version info
    const changelogData = {
        '3.5.4': {  
            fixed: [
                'OpenAI ChatGPT 5 chat error fixed',
            ],
            added: [
                'Drag widget to move it to the desired position',
                'Support languages: Ukrainian, Portuguese, Chinese'
            ],
            changed: [
              'Improved generation of the workflow so that the AI correctly substitutes variables in node settings.',
              'Added a condition for the /update_nodes command so that if the node settings are open, the AI updates the settings for that node.'
            ]
        },
        '3.5.0': {
            fixed: [
                'Fixed bugs',
            ],
            added: [
                '🔥 Important update: Workflow generation directly on canvas! Now AI can: create workflow from text description using your local node base, add nodes to the scheme, change nodes, change settings in bulk, delete nodes. Use ChatGPT for the best results!',
                'Quick commands for working with workflow have been added to the chat.',
                'For the free version, the number of requests to the AI ​​generator is limited to 10 per day.',
                'Added API key support for local models'
            ],
        },
        '3.4.13': {
            fixed: [
                'Automatic selection of code elements on any site',
            ],
            added: [
                'Added support for French language',
                'Added support for German language',
            ],
        },
        '3.3.9': {
            added: [
                'More than 3000 new templates added', 
                'Added template viewer'           
            ],
            fixed: [
                'Workflow settings auto save trigger fixed',
                'Message "Project name cannot be empty" with local projects enabled fixed'
            ]
        },
        '3.2.0': {
            added: [
                'Added 7 day trial period for premium features.',            
            ],
            changed: [
                'Changed the logic of autosave so that autosave works only if there are 3 or more nodes in the scheme.',
            ]
        },
        '3.1.95': {
            added: [
                'Support for Local LLM models - configure custom chat and models endpoints in options',
                'Smart auto-scroll detection in chat - preserves reading position during AI responses',
                'Enhanced API key preservation system to prevent accidental deletion',
                'Stop button for AI requests - manually cancel ongoing AI operations',
                'Improved streaming response handling with proper error management'
            ],
            fixed: [
                'Due to the update of n8n to version 1.100: Fixed autosave, Autopin, Execution select',
                'Fixed bug with auto-scroll in chat',
                'Fixed resetting API key for n8n when saving options'
            ]
        },
        '3.1.63': {
            added: [
                'Added mode of streaming responses from AI, can be disabled in settings.',
                'A Workflow Histories tab has been added to the options page to display a list of all local workflow changes.',
                'Added the ability to change width for chat, and chat now remembers state and is restored on page refresh.'
            ],
            fixed: [
                'Fixed and finalized condition on generation/selection of ready-made templates in the chat.',
                'Fixed cURL export'
            ],
            changed: [
                'Improvements and enhancements to the chat, including visuals.',
            ]
        },
        '3.0.0': {
            added: [
'Support for 3 languages. The extension supports English, Russian and Spanish.',
'AI Error Trigger. Automatically analyzes errors when testing node settings, a detailed context with incoming parameters, node settings and error text is sent to the AI, and it gives a response with a solution in the chat.',
'Local projects. Activates the ability to create folders with projects in the left menu, add schemes to them, move schemes between folders, and delete them from folders. Each folder can be assigned its own color. Works only if the n8n API key is specified in the settings.',
'Local variables. In the left menu, replaces the built-in Variables link with new logic: when clicked, it displays a block where you can add important information, in addition to api keys, which you often use in your schemes, for example, email or Telegram ID. By clicking, you can copy and paste to the desired location. Available quickly by Ctrl + Shift + V for convenient call from node settings.',
'Remember dialog. Enables dialog history in the chat for each workflow, so the AI ​​remembers the context of working with each of your projects.',
'Node execution select. In editing the node output, you can select a specific execution from the execution history, now there is no need to go to Executions, copy the answer and then paste it into the settings to test, now it is done in a couple of clicks. Zaivist from API n8n.',
'Options Page. Added an options page that can be opened from Popup or by right-clicking on the extension icon. On this page, you can:\n',
'- Change the extension language.',
'- Change the AI ​​model for operators to any other that you like.',
'- Specify additional system instructions for context commands. This way, you can refine the functionality of generating prompts, code, json, if the answers from the AI ​​do not suit you.',
'- Export and import extension settings.'
],
            fixed: [
                'Minor fixes',
            ],
            changed: [
'Expand chat. You can expand the chat to the full height of the screen for convenience.',
'Change history, Ouput template have been moved to IndexedDB, which guarantees stable data storage.',
'Better understanding of the context. Now if you open the node settings, the AI ​​will be aware of all its settings and you can immediately ask specific questions about them, for example: "what is this option NAME?".'
            ]

        },
    };
    
    return changelogData;
}

function formatAllChangelogs(allChangelogs, currentVersion) {
    let html = '';
    
    // Sort versions in descending order (newest first)
    const versions = Object.keys(allChangelogs).sort((a, b) => {
        const aNum = parseFloat(a.replace('v', ''));
        const bNum = parseFloat(b.replace('v', ''));
        return bNum - aNum;
    });
    
    versions.forEach((version, index) => {
        const changelog = allChangelogs[version];
        const isCurrentVersion = version === currentVersion;
        
        html += `
            <div class="version-section ${isCurrentVersion ? 'current-version' : 'old-version'}" style="
                margin-bottom: 30px;
                padding: 20px;
                border-radius: 12px;
            ">
                <h3 class="version-title ${isCurrentVersion ? 'current-version-title' : 'old-version-title'}" style="
                    margin: 0 0 15px 0;
                    font-size: 1.3em;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    ${isCurrentVersion ? '🌟' : '📋'} Version ${version}
                    ${isCurrentVersion ? '<span class="current-badge2">CURRENT</span>' : ''}
                </h3>
        `;
        
        if (changelog.fixed && changelog.fixed.length > 0) {
            console.log('🔧 Adding Fixed section for version:', version);
            html += `
                <div class="changelog-section fixed-section" style="margin-bottom: 15px;">
                    <h4 class="changelog-category-title fixed-title" style="color: #ef4444 !important; font-weight: 700 !important;">🔧 Fixed</h4>
                    <ul class="changelog-list" style="margin: 0; padding-left: 20px;">
                        ${changelog.fixed.map(item => `<li class="changelog-item">${item}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (changelog.added && changelog.added.length > 0) {
            console.log('✨ Adding Added section for version:', version);
            html += `
                <div class="changelog-section added-section" style="margin-bottom: 15px;">
                    <h4 class="changelog-category-title added-title" style="color: #22c55e !important; font-weight: 700 !important;">✨ Added</h4>
                    <ul class="changelog-list" style="margin: 0; padding-left: 20px;">
                        ${changelog.added.map(item => `<li class="changelog-item">${item}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (changelog.changed && changelog.changed.length > 0) {
            console.log('🔄 Adding Changed section for version:', version);
            html += `
                <div class="changelog-section changed-section" style="margin-bottom: 15px;">
                    <h4 class="changelog-category-title changed-title" style="color: #f59e0b !important; font-weight: 700 !important;">🔄 Changed</h4>
                    <ul class="changelog-list" style="margin: 0; padding-left: 20px;">
                        ${changelog.changed.map(item => `<li class="changelog-item">${item}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (changelog.technical && changelog.technical.length > 0) {
            console.log('⚙️ Adding Technical section for version:', version);
            html += `
                <div class="changelog-section technical-section" style="margin-bottom: 15px;">
                    <h4 class="changelog-category-title technical-title" style="color: #a855f7 !important; font-weight: 700 !important;">⚙️ Technical Details</h4>
                    <ul class="changelog-list" style="margin: 0; padding-left: 20px;">
                        ${changelog.technical.map(item => `<li class="changelog-item">${item}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        html += '</div>';
    });
    
    return html;
}

function setupEventListeners() {
   
    // View Documentation button
    const viewDocsBtn = document.getElementById('viewDocs');
    if (viewDocsBtn) {
        viewDocsBtn.addEventListener('click', () => {
            chrome.tabs.create({
                url: 'https://fffem.com/tutorial'
            });
        });
    } else {
        console.warn('⚠️ Element with id "viewDocs" not found');
    }
    
    // Close Welcome button
    const closeWelcomeBtn = document.getElementById('closeWelcome');
    if (closeWelcomeBtn) {
        closeWelcomeBtn.addEventListener('click', () => {
            window.close();
        });
    } else {
        console.warn('⚠️ Element with id "closeWelcome" not found');
    }
    
}

// Show settings instructions modal
function showSettingsInstructions() {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    // Create modal content
    const modal = document.createElement('div');
    modal.className = 'settings-modal';
    modal.style.cssText = `
        border-radius: 12px;
        padding: 30px;
        max-width: 500px;
        margin: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        animation: slideIn 0.3s ease;
    `;
    
    modal.innerHTML = `
        <div class="modal-header-section" style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 3em; margin-bottom: 10px;">⚙️</div>
            <h2 class="modal-title" style="margin: 0;" data-i18n="welcome_open_settings">Access Settings</h2>
        </div>
        
        <div class="modal-body-section" style="margin-bottom: 25px;">
            <p class="modal-description" style="margin-bottom: 15px;" data-i18n="modalSettingsDescription">To configure N8N Master settings:</p>
            
            <div class="modal-steps-container" style="padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span class="step-number-modal" style="width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; margin-right: 10px; font-size: 14px;">1</span>
                    <span class="step-text-modal" style="font-weight: 500;" data-i18n="modalStep1">Click the N8N Master extension icon in your browser toolbar</span>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span class="step-number-modal" style="width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; margin-right: 10px; font-size: 14px;">2</span>
                    <span class="step-text-modal" style="font-weight: 500;" data-i18n="modalStep2">Configure your API keys and enable features</span>
                </div>
                
                <div style="display: flex; align-items: center;">
                    <span class="step-number-modal" style="width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; margin-right: 10px; font-size: 14px;">3</span>
                    <span class="step-text-modal" style="font-weight: 500;" data-i18n="modalStep3">Start using N8N Master features</span>
                </div>
            </div>
            
            <div class="modal-tip-container" style="padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                <strong class="modal-tip-title" data-i18n="modalTipTitle">💡 Tip:</strong>
                <span class="modal-tip-text" data-i18n="modalTipText"> If you don't see the extension icon, click the puzzle piece (🧩) in your toolbar and pin N8N Master.</span>
            </div>
        </div>
        
        <div style="text-align: center;">
            <button id="closeModal" class="btn btn-primary modal-close-btn" style="
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease;
            ">
                <span data-i18n="welcome_got_it">Got it!</span>
            </button>
        </div>
    `;
    
    // Add animations and hover effects
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .modal-close-btn:hover {
            transform: translateY(-2px) !important;
        }
        .modal-close-btn:active {
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Localize modal content
    if (window.I18nManager) {
        window.I18nManager.localizeDOM();
    }
    
    // Close modal handlers
    const closeModal = () => {
        overlay.style.animation = 'fadeIn 0.3s ease reverse';
        setTimeout(() => {
            document.body.removeChild(overlay);
            document.head.removeChild(style);
        }, 300);
    };
    
    modal.querySelector('#closeModal').addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    
    // Close on Escape key
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}

// Analytics (optional)
function trackWelcomePageView(installInfo) {
    // You could add analytics here
    console.log('📊 Welcome page viewed:', installInfo);
} 

// Open Options button
const openOptionsBtn = document.getElementById('openOptions');
if (openOptionsBtn) {
    openOptionsBtn.addEventListener('click', () => {
        chrome.runtime.openOptionsPage();
    });
} else {
    console.warn('⚠️ Element with id "openOptions" not found');
}