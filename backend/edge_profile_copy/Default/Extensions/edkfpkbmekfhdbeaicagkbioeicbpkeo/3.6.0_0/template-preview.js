// Template Preview JavaScript
// Handles loading and displaying n8n workflow templates

let currentWorkflowData = null;

// Hide n8n-demo footer after load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize localization
    if (window.I18nManager) {
        window.I18nManager.init();
    }
    
    // Hide n8n-demo footer
    setTimeout(function() {
        const footers = document.querySelectorAll('.workflow-canvas-footer');
        footers.forEach(function(footer) {
            footer.style.display = 'none';
        });
    }, 1000);
    
    // Add event listeners for buttons
    const copyBtn = document.getElementById('copy-btn');
    const downloadBtn = document.getElementById('download-btn');
    const closeBtn = document.getElementById('close-btn');
    
    if (copyBtn) {
        copyBtn.addEventListener('click', copyWorkflowJson);
    }
    
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadWorkflow);
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            window.close();
        });
    }
});

// Get URL parameters
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Load workflow data
async function loadWorkflow() {
    try {
        
        // Get template info from URL parameters
        const templateName = getUrlParameter('name') || 'Unknown Template';
        const templatePath = getUrlParameter('path');
        const workflowJson = getUrlParameter('json');
        
        document.getElementById('template-name').textContent = templateName;
        document.title = `${templateName} - N8N Template Preview`;
        
        let workflowData;
        
        if (workflowJson) {
            // Workflow JSON passed directly
            try {
                workflowData = JSON.parse(decodeURIComponent(workflowJson));            
            } catch (e) {
                throw new Error('Invalid JSON in URL parameter');
            }
        } else if (templatePath) {
            // Load from GitHub using GitHubDownloader
            
            const downloadResult = await GitHubDownloader.downloadWorkflow(templatePath);
            
            if (!downloadResult.success) {
                throw new Error(`Failed to load template: ${downloadResult.error}`);
            }
            
            if (downloadResult.type === 'json' || downloadResult.type === 'json_unknown') {
                workflowData = downloadResult.workflow;
            } else if (downloadResult.type === 'text') {
                // Try to parse text as JSON
                try {
                    workflowData = JSON.parse(downloadResult.workflow);
                } catch (e) {
                    // Try to parse as string (some templates are stored as strings)
                    workflowData = JSON.parse(JSON.parse(downloadResult.workflow));
                }
            } else {
                throw new Error('Unsupported workflow format');
            }
            
        } else {
            throw new Error('No template data provided');
        }
        
        currentWorkflowData = workflowData;
        
        // Update workflow stats
        const nodeCount = workflowData.nodes ? workflowData.nodes.length : 0;
        const connectionCount = workflowData.connections ? 
            Object.values(workflowData.connections).reduce((sum, conn) => 
                sum + (conn.main ? conn.main.reduce((s, c) => s + c.length, 0) : 0), 0) : 0;
        
        document.getElementById('node-count').textContent = nodeCount;
        document.getElementById('connection-count').textContent = connectionCount;
        document.getElementById('workflow-stats').style.display = 'block';
        
        // Wait for n8n-demo component to be ready
        await waitForN8nDemo();
        
        // Set workflow data
        const demoElement = document.getElementById('workflow-demo');
        demoElement.setAttribute('workflow', JSON.stringify(workflowData));
        
        // Hide loading overlay
        document.getElementById('loading-overlay').style.display = 'none';
        
    } catch (error) {
        console.error('❌ [TEMPLATE PREVIEW] Error loading workflow:', error);
        showError(error.message);
    }
}

// Wait for n8n-demo component to be available
function waitForN8nDemo() {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const maxAttempts = 50;
        
        const checkComponent = () => {
            attempts++;
            
            if (window.customElements && window.customElements.get('n8n-demo')) {
                resolve();
            } else if (attempts >= maxAttempts) {
                reject(new Error('n8n-demo component failed to load'));
            } else {
                setTimeout(checkComponent, 200);
            }
        };
        
        checkComponent();
    });
}

// Show error message
function showError(message) {
    document.getElementById('loading-overlay').style.display = 'none';
    document.getElementById('error-details').textContent = message;
    document.getElementById('error-message').style.display = 'block';
}

// Copy workflow JSON to clipboard
async function copyWorkflowJson(event) {
    if (!currentWorkflowData) {
        alert('No workflow data available');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(JSON.stringify(currentWorkflowData, null, 2));
        
        // Show success feedback
        const btn = event.target.closest('.btn') || event.target;
        const originalText = btn.innerHTML;
        const copiedText = window.I18nManager ? window.I18nManager.getMessage('copied') || 'Copied!' : 'Copied!';
        btn.innerHTML = `<span class="btn-icon">✅</span> <span>${copiedText}</span>`;
        btn.style.background = '#48bb78';
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.background = '';
        }, 2000);
        
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        alert('Failed to copy to clipboard');
    }
}

// Download workflow as JSON file
function downloadWorkflow() {
    if (!currentWorkflowData) {
        alert('No workflow data available');
        return;
    }
    
    const templateName = document.getElementById('template-name').textContent || 'workflow';
    const filename = `${templateName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.json`;
    
    const blob = new Blob([JSON.stringify(currentWorkflowData, null, 2)], {
        type: 'application/json'
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Initialize when page loads
window.addEventListener('load', () => {
    // Add small delay to ensure all scripts are loaded
    setTimeout(loadWorkflow, 500);
});