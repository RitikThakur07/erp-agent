// Global state
let currentProjectId = null;
let currentFilePath = null;
let editor = null;

// Initialize Monaco Editor
require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});

require(['vs/editor/editor.main'], function() {
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: '// Select a file to edit',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false }
    });
});

// Project management
function showNewProjectDialog() {
    document.getElementById('new-project-dialog').classList.remove('hidden');
}

function hideNewProjectDialog() {
    document.getElementById('new-project-dialog').classList.add('hidden');
}

async function createProject(event) {
    event.preventDefault();
    
    const name = document.getElementById('project-name').value;
    const description = document.getElementById('project-description').value;
    
    try {
        const response = await fetch('/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        
        const data = await response.json();
        
        if (data.project_id) {
            // Add to select dropdown
            const select = document.getElementById('project-select');
            const option = document.createElement('option');
            option.value = data.project_id;
            option.textContent = name;
            select.appendChild(option);
            select.value = data.project_id;
            
            // Load project
            await loadProject(data.project_id);
            
            hideNewProjectDialog();
            document.getElementById('new-project-form').reset();
        }
    } catch (error) {
        alert('Failed to create project: ' + error.message);
    }
}

// Project selection
document.getElementById('project-select').addEventListener('change', async (e) => {
    const projectId = e.target.value;
    if (projectId) {
        await loadProject(projectId);
    }
});

async function loadProject(projectId) {
    currentProjectId = projectId;
    
    // Update status
    updateStatus('Loading project...');
    
    try {
        // Load project details
        const response = await fetch(`/projects/${projectId}`);
        const project = await response.json();
        
        // Update status
        let status = `Project: ${project.name} | Status: ${project.status}`;
        updateStatus(status);
        
        // Load file tree
        await loadFileTree(projectId);
        
        // Enable/disable buttons based on project state
        document.getElementById('btn-backend').disabled = !project.prd;
        document.getElementById('btn-frontend').disabled = !project.prd;
        document.getElementById('btn-qa').disabled = !project.backend_generated;
        
    } catch (error) {
        updateStatus('Error loading project');
        console.error(error);
    }
}

async function loadFileTree(projectId) {
    try {
        const response = await fetch(`/projects/${projectId}/file-tree`);
        const tree = await response.json();
        
        const treeContainer = document.getElementById('file-tree');
        treeContainer.innerHTML = '';
        
        if (tree.name) {
            renderTree(tree, treeContainer);
        } else {
            treeContainer.innerHTML = '<p class="text-sm text-gray-500">No files generated yet</p>';
        }
    } catch (error) {
        console.error('Failed to load file tree:', error);
    }
}

function renderTree(node, container, level = 0) {
    const div = document.createElement('div');
    div.className = 'file-item';
    div.style.paddingLeft = `${level * 16}px`;
    
    if (node.type === 'directory') {
        div.innerHTML = `📁 ${node.name}`;
        container.appendChild(div);
        
        if (node.children) {
            node.children.forEach(child => renderTree(child, container, level + 1));
        }
    } else {
        div.innerHTML = `📄 ${node.name}`;
        div.onclick = () => loadFile(node.path);
        container.appendChild(div);
    }
}

async function loadFile(filePath) {
    if (!currentProjectId) return;
    
    try {
        const response = await fetch(`/projects/${currentProjectId}/file?path=${encodeURIComponent(filePath)}`);
        const data = await response.json();
        
        currentFilePath = filePath;
        
        // Determine language
        const ext = filePath.split('.').pop();
        const languageMap = {
            'py': 'python',
            'js': 'javascript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown'
        };
        
        const language = languageMap[ext] || 'plaintext';
        
        // Update editor
        monaco.editor.setModelLanguage(editor.getModel(), language);
        editor.setValue(data.content);
        
        document.getElementById('current-file').textContent = filePath;
        
    } catch (error) {
        alert('Failed to load file: ' + error.message);
    }
}

async function saveFile() {
    if (!currentProjectId || !currentFilePath) {
        alert('No file selected');
        return;
    }
    
    const content = editor.getValue();
    
    try {
        await fetch(`/projects/${currentProjectId}/file`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: currentFilePath, content })
        });
        
        updateStatus('File saved successfully');
    } catch (error) {
        alert('Failed to save file: ' + error.message);
    }
}

// Chat functionality
async function sendMessage(event) {
    event.preventDefault();
    
    if (!currentProjectId) {
        alert('Please select or create a project first');
        return;
    }
    
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Clear input
    input.value = '';
    
    // Send to backend
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId, message })
        });
        
        const data = await response.json();
        
        // Add assistant response
        addMessageToChat('assistant', data.message);
        
        // Check if PRD was generated
        if (data.is_prd) {
            updateStatus('PRD generated - ready to generate code');
            document.getElementById('btn-backend').disabled = false;
            document.getElementById('btn-frontend').disabled = false;
        }
        
    } catch (error) {
        addMessageToChat('assistant', 'Sorry, I encountered an error: ' + error.message);
    }
}

function addMessageToChat(role, message) {
    const messagesDiv = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    
    const p = document.createElement('p');
    p.className = 'text-sm';
    p.textContent = message;
    
    messageDiv.appendChild(p);
    messagesDiv.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function generatePRD() {
    if (!currentProjectId) {
        alert('Please select a project first');
        return;
    }
    
    updateStatus('Generating PRD...');
    
    try {
        const response = await fetch('/chat/generate-prd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessageToChat('assistant', 'PRD generated successfully! You can now generate backend and frontend code.');
            updateStatus('PRD ready');
            document.getElementById('btn-backend').disabled = false;
            document.getElementById('btn-frontend').disabled = false;
        } else {
            addMessageToChat('assistant', 'Failed to generate PRD: ' + data.error);
        }
        
    } catch (error) {
        addMessageToChat('assistant', 'Error generating PRD: ' + error.message);
    }
}

// Agent triggers
async function generateBackend() {
    if (!currentProjectId) return;
    
    updateStatus('Generating backend code...');
    disableButtons();
    
    try {
        const response = await fetch('/agent/backend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessageToChat('assistant', '✅ Backend code generated successfully!');
            updateStatus('Backend generated');
            await loadFileTree(currentProjectId);
            document.getElementById('btn-qa').disabled = false;
        } else {
            addMessageToChat('assistant', '❌ Backend generation failed: ' + data.error);
        }
        
    } catch (error) {
        addMessageToChat('assistant', 'Error: ' + error.message);
    } finally {
        enableButtons();
    }
}

async function generateFrontend() {
    if (!currentProjectId) return;
    
    updateStatus('Generating frontend code...');
    disableButtons();
    
    try {
        const response = await fetch('/agent/frontend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessageToChat('assistant', '✅ Frontend code generated successfully!');
            updateStatus('Frontend generated');
            await loadFileTree(currentProjectId);
            
            // Load preview
            loadPreview();
        } else {
            addMessageToChat('assistant', '❌ Frontend generation failed: ' + data.error);
        }
        
    } catch (error) {
        addMessageToChat('assistant', 'Error: ' + error.message);
    } finally {
        enableButtons();
    }
}

async function runQA() {
    if (!currentProjectId) return;
    
    updateStatus('Running QA tests...');
    disableButtons();
    
    try {
        const response = await fetch('/agent/qa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const results = data.qa_results;
            let message = '✅ QA Complete!\n\n';
            message += `Tests Generated: ${results.tests_generated.length} files\n`;
            
            if (results.code_validation) {
                message += `Files Checked: ${results.code_validation.files_checked}\n`;
                message += `Issues Found: ${results.code_validation.total_issues}`;
            }
            
            addMessageToChat('assistant', message);
            updateStatus('QA complete');
            await loadFileTree(currentProjectId);
        } else {
            addMessageToChat('assistant', '❌ QA failed: ' + data.error);
        }
        
    } catch (error) {
        addMessageToChat('assistant', 'Error: ' + error.message);
    } finally {
        enableButtons();
    }
}

function loadPreview() {
    if (!currentProjectId) return;
    
    const iframe = document.getElementById('preview-frame');
    iframe.src = `/preview/${currentProjectId}/templates/dashboard.html`;
}

// File upload
async function uploadDocument() {
    if (!currentProjectId) {
        alert('Please select a project first');
        return;
    }
    
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.docx,.xlsx,.txt,.md';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        updateStatus('Uploading document...');
        
        try {
            const response = await fetch(`/upload?project_id=${currentProjectId}`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                addMessageToChat('assistant', `✅ Document "${data.filename}" uploaded and processed successfully!`);
                updateStatus('Document uploaded');
            } else {
                addMessageToChat('assistant', `❌ Upload failed: ${data.error}`);
            }
            
        } catch (error) {
            addMessageToChat('assistant', 'Upload error: ' + error.message);
        }
    };
    
    input.click();
}

// Utility functions
function updateStatus(text) {
    document.getElementById('status-text').textContent = text;
}

function disableButtons() {
    document.getElementById('btn-backend').disabled = true;
    document.getElementById('btn-frontend').disabled = true;
    document.getElementById('btn-qa').disabled = true;
}

function enableButtons() {
    // Re-enable based on project state
    if (currentProjectId) {
        loadProject(currentProjectId);
    }
}
