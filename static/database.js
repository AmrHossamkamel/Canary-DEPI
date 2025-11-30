// Database Management UI - JavaScript Controller
class DatabaseManager {
    constructor() {
        this.endpoint = '';
        this.secretKey = '';
        this.isConnected = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSavedConfig();
        this.checkForScrapingResults();
        this.loadSavedQueries();
    }
    
    bindEvents() {
        // Database configuration form
        const dbConfigForm = document.getElementById('dbConfigForm');
        dbConfigForm.addEventListener('submit', (e) => this.handleConfigSubmit(e));
        
        // Query execution form
        const queryForm = document.getElementById('queryForm');
        queryForm.addEventListener('submit', (e) => this.handleQuerySubmit(e));
        
        // Action buttons
        const downloadResultsBtn = document.getElementById('downloadResultsBtn');
        const clearResultsBtn = document.getElementById('clearResultsBtn');
        
        downloadResultsBtn.addEventListener('click', () => this.downloadResults());
        clearResultsBtn.addEventListener('click', () => this.clearResults());
        
        // Save/Load query buttons
        const saveQueryBtn = document.getElementById('saveQueryBtn');
        const clearSavedBtn = document.getElementById('clearSavedBtn');
        const autoFillBtn = document.getElementById('autoFillVariablesBtn');
        
        if (saveQueryBtn) saveQueryBtn.addEventListener('click', () => this.saveCurrentQuery());
        if (clearSavedBtn) clearSavedBtn.addEventListener('click', () => this.clearSavedQueries());
        if (autoFillBtn) autoFillBtn.addEventListener('click', () => this.autoFillVariables());
        
        // Import scraping data button
        const importBtn = document.createElement('button');
        importBtn.className = 'action-btn';
        importBtn.innerHTML = '📊 استيراد بيانات Web Scraping';
        importBtn.addEventListener('click', () => this.importScrapingData());
        
        // Add to query interface when it's shown
        setTimeout(() => {
            const queryActions = document.querySelector('#queryInterface .results-actions');
            if (queryActions && !document.getElementById('importScrapingBtn')) {
                importBtn.id = 'importScrapingBtn';
                queryActions.appendChild(importBtn);
            }
        }, 100);
        
        // Auto-save configuration
        const endpointInput = document.getElementById('endpoint');
        const secretKeyInput = document.getElementById('secretKey');
        
        endpointInput.addEventListener('input', () => this.saveConfig());
        secretKeyInput.addEventListener('input', () => this.saveConfig());
    }
    
    loadSavedConfig() {
        const savedEndpoint = localStorage.getItem('hasura_endpoint');
        const savedSecretKey = localStorage.getItem('hasura_secret_key');
        
        if (savedEndpoint) {
            document.getElementById('endpoint').value = savedEndpoint;
            this.endpoint = savedEndpoint;
        }
        
        if (savedSecretKey) {
            document.getElementById('secretKey').value = savedSecretKey;
            this.secretKey = savedSecretKey;
        }
        
        if (savedEndpoint && savedSecretKey) {
            this.testConnection(false);
        }
    }
    
    saveConfig() {
        const endpoint = document.getElementById('endpoint').value;
        const secretKey = document.getElementById('secretKey').value;
        
        if (endpoint) localStorage.setItem('hasura_endpoint', endpoint);
        if (secretKey) localStorage.setItem('hasura_secret_key', secretKey);
        
        this.endpoint = endpoint;
        this.secretKey = secretKey;
    }
    
    async handleConfigSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        this.endpoint = formData.get('endpoint');
        this.secretKey = formData.get('secretKey');
        
        await this.testConnection(true);
    }
    
    async testConnection(showNotification = true) {
        const connectBtn = document.getElementById('connectBtn');
        const statusDot = document.getElementById('dbStatusDot');
        const statusText = document.getElementById('dbStatusText');
        
        try {
            connectBtn.classList.add('loading');
            statusDot.className = 'status-dot checking';
            statusText.textContent = 'جاري الاتصال...';
            
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-hasura-admin-secret': this.secretKey
                },
                body: JSON.stringify({
                    query: `
                        query {
                            __schema {
                                queryType {
                                    name
                                }
                            }
                        }
                    `
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.data) {
                statusDot.className = 'status-dot';
                statusText.textContent = 'متصل ✓';
                this.isConnected = true;
                
                if (showNotification) {
                    this.showNotification('تم الاتصال بقاعدة البيانات بنجاح', 'success');
                }
                
                this.showQueryInterface();
                this.loadSchema();
                
            } else {
                throw new Error(data.error || 'فشل في الاتصال');
            }
            
        } catch (error) {
            statusDot.className = 'status-dot error';
            statusText.textContent = 'فشل الاتصال ✗';
            this.isConnected = false;
            
            if (showNotification) {
                this.showNotification(`خطأ في الاتصال: ${error.message}`, 'error');
            }
            
        } finally {
            connectBtn.classList.remove('loading');
        }
    }
    
    showQueryInterface() {
        const queryInterface = document.getElementById('queryInterface');
        queryInterface.style.display = 'block';
        queryInterface.scrollIntoView({ behavior: 'smooth' });
    }
    
    async loadSchema() {
        try {
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-hasura-admin-secret': this.secretKey
                },
                body: JSON.stringify({
                    query: `
                        query {
                            __schema {
                                types {
                                    name
                                    kind
                                    fields {
                                        name
                                        type {
                                            name
                                            kind
                                        }
                                    }
                                }
                            }
                        }
                    `
                })
            });
            
            const data = await response.json();
            
            if (data.data) {
                this.displaySchema(data.data.__schema.types);
            }
            
        } catch (error) {
            console.error('Error loading schema:', error);
        }
    }
    
    displaySchema(types) {
        const schemaContent = document.getElementById('schemaContent');
        
        // Filter out system types
        const userTypes = types.filter(type => 
            !type.name.startsWith('__') && 
            type.kind === 'OBJECT' && 
            type.fields && 
            type.fields.length > 0
        );
        
        let html = '<div class="schema-types">';
        
        userTypes.forEach(type => {
            html += `
                <div class="example-query">
                    <h4>📋 ${type.name}</h4>
                    <div style="margin-top: 0.5rem; font-size: 0.9em;">
            `;
            
            type.fields.forEach(field => {
                const fieldType = field.type.name || field.type.kind;
                html += `
                    <div style="margin: 0.2rem 0; color: rgba(255,255,255,0.8);">
                        • <span style="color: #f093fb;">${field.name}</span>: 
                        <span style="color: #4facfe;">${fieldType}</span>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        schemaContent.innerHTML = html;
    }
    
    async handleQuerySubmit(event) {
        event.preventDefault();
        
        if (!this.isConnected) {
            this.showNotification('يرجى الاتصال بقاعدة البيانات أولاً', 'warning');
            return;
        }
        
        const formData = new FormData(event.target);
        const query = formData.get('graphqlQuery');
        const variablesText = formData.get('variables');
        
        let variables = {};
        if (variablesText.trim()) {
            try {
                variables = JSON.parse(variablesText);
                
                // If we have scraping data, auto-fill the template variables
                if (this.scrapingData && this.scrapingData.length > 0) {
                    const firstItem = this.scrapingData[0].data;
                    variables = this.generateVariablesFromData(variablesText, firstItem);
                }
                
            } catch (error) {
                this.showNotification('خطأ في تنسيق Variables JSON', 'error');
                return;
            }
        } else if (this.scrapingData && this.scrapingData.length > 0) {
            // If no variables template but we have scraping data, use first item
            variables = this.scrapingData[0].data;
        }
        
        await this.executeQuery(query, variables);
    }
    
    async executeQuery(query, variables = {}) {
        const executeBtn = document.getElementById('executeBtn');
        const queryResults = document.getElementById('queryResults');
        const responseViewer = document.getElementById('responseViewer');
        
        try {
            executeBtn.classList.add('loading');
            
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-hasura-admin-secret': this.secretKey
                },
                body: JSON.stringify({
                    query: query,
                    variables: variables
                })
            });
            
            const data = await response.json();
            
            // Show results section
            queryResults.style.display = 'block';
            queryResults.scrollIntoView({ behavior: 'smooth' });
            
            // Display formatted response
            const formattedResponse = this.formatJSON(data);
            responseViewer.innerHTML = formattedResponse;
            
            if (data.errors) {
                this.showNotification('Query executed with errors - check results', 'warning');
            } else {
                this.showNotification('Query executed successfully', 'success');
            }
            
            // Store results for download
            this.lastResults = data;
            
        } catch (error) {
            this.showNotification(`خطأ في تنفيذ Query: ${error.message}`, 'error');
            
        } finally {
            executeBtn.classList.remove('loading');
        }
    }
    
    formatJSON(obj, indent = 0) {
        const spaces = '  '.repeat(indent);
        
        if (obj === null) return '<span class="json-null">null</span>';
        if (typeof obj === 'boolean') return `<span class="json-boolean">${obj}</span>`;
        if (typeof obj === 'number') return `<span class="json-number">${obj}</span>`;
        if (typeof obj === 'string') return `<span class="json-string">"${obj}"</span>`;
        
        if (Array.isArray(obj)) {
            if (obj.length === 0) return '[]';
            
            let result = '[\n';
            obj.forEach((item, index) => {
                result += `${spaces}  ${this.formatJSON(item, indent + 1)}`;
                if (index < obj.length - 1) result += ',';
                result += '\n';
            });
            result += `${spaces}]`;
            return result;
        }
        
        if (typeof obj === 'object') {
            const keys = Object.keys(obj);
            if (keys.length === 0) return '{}';
            
            let result = '{\n';
            keys.forEach((key, index) => {
                result += `${spaces}  <span class="json-key">"${key}"</span>: ${this.formatJSON(obj[key], indent + 1)}`;
                if (index < keys.length - 1) result += ',';
                result += '\n';
            });
            result += `${spaces}}`;
            return result;
        }
        
        return String(obj);
    }
    
    downloadResults() {
        if (!this.lastResults) {
            this.showNotification('لا توجد نتائج للتحميل', 'warning');
            return;
        }
        
        const dataStr = JSON.stringify(this.lastResults, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `query-results-${new Date().toISOString().slice(0, 10)}.json`;
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showNotification('تم تحميل النتائج بنجاح', 'success');
    }
    
    clearResults() {
        const queryResults = document.getElementById('queryResults');
        const responseViewer = document.getElementById('responseViewer');
        
        queryResults.style.display = 'none';
        responseViewer.innerHTML = '';
        this.lastResults = null;
        
        this.showNotification('تم مسح النتائج', 'success');
    }
    
    checkForScrapingResults() {
        const scrapingResults = localStorage.getItem('scraping_results');
        if (scrapingResults) {
            try {
                const results = JSON.parse(scrapingResults);
                this.scrapingData = results;
                
                // Show notification
                setTimeout(() => {
                    this.showNotification(`تم العثور على ${results.length} نتيجة من Web Scraping - اضغط "استيراد بيانات" لاستخدامها`, 'success');
                }, 1000);
                
            } catch (error) {
                console.error('Error parsing scraping results:', error);
            }
        }
    }
    
    importScrapingData() {
        if (!this.scrapingData || this.scrapingData.length === 0) {
            this.showNotification('لا توجد بيانات Web Scraping للاستيراد', 'warning');
            return;
        }
        
        // Generate the mutation query
        const mutation = `mutation InsertData($content: String, $source_url: String, $title: String) {
  insert_data(objects: {content: $content, source_url: $source_url, title: $title}) {
    affected_rows
    returning {
      id
      content
      source_url
      title
      created_at
    }
  }
}`;
        
        // Fill the query editor
        document.getElementById('graphqlQuery').value = mutation;
        
        // Generate variables for the first item as example
        const firstItem = this.scrapingData[0].data;
        const variables = {
            content: firstItem.content || "",
            source_url: firstItem.source_url || "",
            title: firstItem.title || ""
        };
        
        document.getElementById('variables').value = JSON.stringify(variables, null, 2);
        
        // Switch to query tab
        switchTab('query');
        
        // Scroll to query editor
        document.getElementById('graphqlQuery').scrollIntoView({ behavior: 'smooth' });
        
        this.showNotification(`تم استيراد البيانات! يمكنك الآن إرسال ${this.scrapingData.length} عنصر لقاعدة البيانات`, 'success');
        
        // Show bulk insert option
        this.showBulkInsertOption();
    }
    
    showBulkInsertOption() {
        // Create bulk insert button if it doesn't exist
        if (!document.getElementById('bulkInsertBtn')) {
            const bulkBtn = document.createElement('button');
            bulkBtn.id = 'bulkInsertBtn';
            bulkBtn.className = 'submit-btn';
            bulkBtn.style.marginTop = '1rem';
            bulkBtn.innerHTML = `
                <span class="btn-icon">📦</span>
                <span class="btn-text">إرسال جميع البيانات (${this.scrapingData.length} عنصر)</span>
                <div class="btn-loader"></div>
            `;
            
            bulkBtn.addEventListener('click', () => this.executeBulkInsert());
            
            // Add after the regular execute button
            const executeBtn = document.getElementById('executeBtn');
            executeBtn.parentNode.insertBefore(bulkBtn, executeBtn.nextSibling);
        }
    }
    
    async executeBulkInsert() {
        if (!this.isConnected) {
            this.showNotification('يرجى الاتصال بقاعدة البيانات أولاً', 'warning');
            return;
        }
        
        if (!this.scrapingData || this.scrapingData.length === 0) {
            this.showNotification('لا توجد بيانات للإرسال', 'warning');
            return;
        }
        
        const bulkBtn = document.getElementById('bulkInsertBtn');
        bulkBtn.classList.add('loading');
        
        // Get current query and variables
        const queryTemplate = document.getElementById('graphqlQuery').value.trim();
        const variablesTemplate = document.getElementById('variables').value.trim();
        
        if (!queryTemplate) {
            this.showNotification('يرجى كتابة Query أولاً', 'warning');
            bulkBtn.classList.remove('loading');
            return;
        }
        
        let successCount = 0;
        let errorCount = 0;
        
        try {
            // Process each item
            for (let i = 0; i < this.scrapingData.length; i++) {
                const item = this.scrapingData[i].data;
                
                try {
                    // Generate variables from JSON data automatically
                    const variables = this.generateVariablesFromData(variablesTemplate, item);
                    
                    const response = await fetch(this.endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'x-hasura-admin-secret': this.secretKey
                        },
                        body: JSON.stringify({
                            query: queryTemplate,
                            variables: variables
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.errors) {
                        errorCount++;
                        console.error(`Error inserting item ${i + 1}:`, data.errors);
                    } else {
                        successCount++;
                    }
                    
                } catch (itemError) {
                    errorCount++;
                    console.error(`Failed to insert item ${i + 1}:`, itemError);
                }
                
                // Update button text with progress
                const progressText = `معالجة ${i + 1}/${this.scrapingData.length}...`;
                bulkBtn.querySelector('.btn-text').textContent = progressText;
            }
            
            // Show final results
            if (successCount > 0) {
                this.showNotification(`تم إرسال ${successCount} عنصر بنجاح${errorCount > 0 ? ` (${errorCount} فشل)` : ''}`, 'success');
                
                // Clear scraping data after successful insert
                localStorage.removeItem('scraping_results');
                this.scrapingData = null;
                
                // Remove bulk insert button
                bulkBtn.remove();
                
            } else {
                this.showNotification(`فشل في إرسال جميع البيانات (${errorCount} خطأ)`, 'error');
            }
            
        } catch (error) {
            this.showNotification(`خطأ في العملية: ${error.message}`, 'error');
            
        } finally {
            bulkBtn.classList.remove('loading');
            bulkBtn.querySelector('.btn-text').textContent = `إرسال جميع البيانات (${this.scrapingData?.length || 0} عنصر)`;
        }
    }
    
    generateVariablesFromData(variablesTemplate, jsonData) {
        try {
            // Parse the variables template
            let variables = {};
            
            if (variablesTemplate) {
                variables = JSON.parse(variablesTemplate);
            } else {
                // If no template, return the JSON data directly
                return jsonData;
            }
            
            // Only fill the variables that exist in the template
            for (const templateKey in variables) {
                // Look for exact match first
                if (jsonData.hasOwnProperty(templateKey)) {
                    variables[templateKey] = jsonData[templateKey] || "";
                } else {
                    // Try to find matching key (case insensitive)
                    const dataKeys = Object.keys(jsonData);
                    const matchingKey = dataKeys.find(k => 
                        k.toLowerCase() === templateKey.toLowerCase()
                    );
                    
                    if (matchingKey) {
                        variables[templateKey] = jsonData[matchingKey] || "";
                    } else {
                        // Keep original value if no match found
                        variables[templateKey] = variables[templateKey] || "";
                    }
                }
            }
            
            return variables;
            
        } catch (error) {
            console.error('Error generating variables:', error);
            // Fallback: return the JSON data directly
            return jsonData;
        }
    }

    saveCurrentQuery() {
        const queryText = document.getElementById('graphqlQuery').value.trim();
        const variablesText = document.getElementById('variables').value.trim();
        const queryName = document.getElementById('queryName').value.trim() || `Query ${new Date().toLocaleString('ar-EG')}`;
        
        if (!queryText) {
            this.showNotification('لا يوجد query لحفظه', 'warning');
            return;
        }
        
        // Get saved queries from localStorage
        let savedQueries = JSON.parse(localStorage.getItem('hasura_saved_queries') || '[]');
        
        // Create new query object
        const newQuery = {
            id: Date.now(),
            name: queryName,
            query: queryText,
            variables: variablesText,
            createdAt: new Date().toISOString()
        };
        
        // Add to saved queries
        savedQueries.unshift(newQuery); // Add to beginning
        
        // Keep only last 20 queries
        if (savedQueries.length > 20) {
            savedQueries = savedQueries.slice(0, 20);
        }
        
        // Save to localStorage
        localStorage.setItem('hasura_saved_queries', JSON.stringify(savedQueries));
        
        // Refresh the display
        this.loadSavedQueries();
        
        // Clear query name field
        document.getElementById('queryName').value = '';
        
        this.showNotification(`تم حفظ Query: ${queryName}`, 'success');
    }
    
    loadSavedQueries() {
        const savedQueries = JSON.parse(localStorage.getItem('hasura_saved_queries') || '[]');
        const container = document.getElementById('savedQueriesList');
        
        if (savedQueries.length === 0) {
            container.innerHTML = '<p style="color: rgba(255,255,255,0.6); font-style: italic;">لا توجد queries محفوظة</p>';
            return;
        }
        
        let html = '';
        savedQueries.forEach(savedQuery => {
            const date = new Date(savedQuery.createdAt).toLocaleDateString('ar-EG');
            const time = new Date(savedQuery.createdAt).toLocaleTimeString('ar-EG', {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            html += `
                <div class="example-query" style="position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                        <h4 style="margin: 0; color: #f093fb;">📄 ${savedQuery.name}</h4>
                        <div style="display: flex; gap: 0.5rem;">
                            <button 
                                class="action-btn" 
                                style="padding: 0.25rem 0.5rem; font-size: 11px; background: rgba(255,255,255,0.1);"
                                onclick="window.databaseManager.loadSavedQuery(${savedQuery.id})"
                            >
                                📂 تحميل
                            </button>
                            <button 
                                class="action-btn" 
                                style="padding: 0.25rem 0.5rem; font-size: 11px; background: rgba(255,0,0,0.2);"
                                onclick="window.databaseManager.deleteSavedQuery(${savedQuery.id})"
                            >
                                🗑️ حذف
                            </button>
                        </div>
                    </div>
                    <div style="font-size: 11px; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem;">
                        ${date} - ${time}
                    </div>
                    <pre style="font-size: 11px; max-height: 100px; overflow-y: auto; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 4px; margin: 0;">${savedQuery.query}</pre>
                    ${savedQuery.variables ? `<div style="margin-top: 0.5rem;"><strong style="font-size: 11px; color: #4facfe;">Variables:</strong><pre style="font-size: 10px; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 4px; margin: 0.25rem 0 0 0; max-height: 60px; overflow-y: auto;">${savedQuery.variables}</pre></div>` : ''}
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    loadSavedQuery(queryId) {
        const savedQueries = JSON.parse(localStorage.getItem('hasura_saved_queries') || '[]');
        const query = savedQueries.find(q => q.id === queryId);
        
        if (!query) {
            this.showNotification('Query غير موجود', 'error');
            return;
        }
        
        // Load into editors
        document.getElementById('graphqlQuery').value = query.query;
        document.getElementById('variables').value = query.variables || '';
        document.getElementById('queryName').value = query.name;
        
        // Scroll to query editor
        document.getElementById('graphqlQuery').scrollIntoView({ behavior: 'smooth' });
        
        this.showNotification(`تم تحميل Query: ${query.name}`, 'success');
    }
    
    deleteSavedQuery(queryId) {
        if (!confirm('هل أنت متأكد من حذف هذا Query؟')) {
            return;
        }
        
        let savedQueries = JSON.parse(localStorage.getItem('hasura_saved_queries') || '[]');
        const queryName = savedQueries.find(q => q.id === queryId)?.name || 'Query';
        
        savedQueries = savedQueries.filter(q => q.id !== queryId);
        localStorage.setItem('hasura_saved_queries', JSON.stringify(savedQueries));
        
        this.loadSavedQueries();
        this.showNotification(`تم حذف Query: ${queryName}`, 'success');
    }
    
    clearSavedQueries() {
        if (!confirm('هل أنت متأكد من حذف جميع Queries المحفوظة؟')) {
            return;
        }
        
        localStorage.removeItem('hasura_saved_queries');
        this.loadSavedQueries();
        this.showNotification('تم حذف جميع Queries المحفوظة', 'success');
    }
    
    autoFillVariables() {
        if (!this.scrapingData || this.scrapingData.length === 0) {
            this.showNotification('لا توجد بيانات Web Scraping للملء التلقائي', 'warning');
            return;
        }
        
        const variablesTextarea = document.getElementById('variables');
        const currentVariables = variablesTextarea.value.trim();
        
        // Get first item data as sample
        const sampleData = this.scrapingData[0].data;
        
        let newVariables = {};
        
        try {
            // If there are existing variables, parse them first
            if (currentVariables) {
                newVariables = JSON.parse(currentVariables);
            }
            
            // Auto-fill only the variables that already exist in template
            Object.keys(newVariables).forEach(templateKey => {
                // Look for exact match in sample data
                if (sampleData.hasOwnProperty(templateKey)) {
                    newVariables[templateKey] = sampleData[templateKey] || "";
                } else {
                    // Try case insensitive match
                    const sampleKeys = Object.keys(sampleData);
                    const matchingKey = sampleKeys.find(k => 
                        k.toLowerCase() === templateKey.toLowerCase()
                    );
                    
                    if (matchingKey) {
                        newVariables[templateKey] = sampleData[matchingKey] || "";
                    }
                }
            });
            
            // Update textarea with formatted JSON
            variablesTextarea.value = JSON.stringify(newVariables, null, 2);
            
            this.showNotification(`تم ملء المتغيرات تلقائياً من بيانات العنصر الأول (${Object.keys(newVariables).length} متغير)`, 'success');
            
        } catch (error) {
            // If parsing fails, create fresh variables from sample data
            variablesTextarea.value = JSON.stringify(sampleData, null, 2);
            this.showNotification(`تم إنشاء متغيرات جديدة من البيانات (${Object.keys(sampleData).length} متغير)`, 'success');
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer');
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
        
        // Click to dismiss
        notification.addEventListener('click', () => {
            notification.remove();
        });
    }
}

// Tab switching function
function switchTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => button.classList.remove('active'));
    
    // Show selected tab content
    document.getElementById(tabName + 'Tab').classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

// Use example query
function useExample(element) {
    const queryText = element.querySelector('pre').textContent;
    document.getElementById('graphqlQuery').value = queryText.trim();
    
    // Switch to query tab
    switchTab('query');
    document.querySelector('.tab-button').classList.remove('active');
    document.querySelector('.tab-button').classList.add('active');
    
    // Scroll to query editor
    document.getElementById('graphqlQuery').scrollIntoView({ behavior: 'smooth' });
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.databaseManager = new DatabaseManager();
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatabaseManager;
}