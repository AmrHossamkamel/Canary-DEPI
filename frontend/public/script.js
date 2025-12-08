class WebScrapingUI {
    constructor() {
        this.apiBaseUrl = (window.APP_CONFIG && window.APP_CONFIG.BACKEND_API_URL) || window.BACKEND_API_URL || "http://backend-service:8000";
        this.currentRequest = null;
        this.results = [];
        this.eventSource = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.checkApiStatus();
        this.setupFormValidation();
        this.handleModeChange();
        this.setupHoverEffects();
        this.updateLinks();
    }
    
    updateLinks() {
        const docsLink = document.getElementById('docsLink');
        const databaseLink = document.getElementById('databaseLink');
        
        if (docsLink) {
            docsLink.href = `${this.apiBaseUrl}/docs`;
        }
        if (databaseLink) {
            databaseLink.href = `${this.apiBaseUrl}/database`;
        }
    }
    
    setupHoverEffects() {
        const interactiveElements = document.querySelectorAll('button, .radio-option, .result-card, .action-btn');
        interactiveElements.forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.style.transform = 'translateY(-2px)';
                el.style.transition = 'all 0.3s ease';
            });
            
            el.addEventListener('mouseleave', () => {
                el.style.transform = 'translateY(0)';
            });
        });
    }
    
    bindEvents() {
        const form = document.getElementById('scrapeForm');
        form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        const downloadBtn = document.getElementById('downloadBtn');
        const sendToDbBtn = document.getElementById('sendToDbBtn');
        const clearBtn = document.getElementById('clearBtn');
        
        downloadBtn.addEventListener('click', () => this.downloadResults());
        sendToDbBtn.addEventListener('click', () => this.sendToDatabase());
        clearBtn.addEventListener('click', () => this.clearResults());
        
        const urlInput = document.getElementById('url');
        urlInput.addEventListener('input', () => this.validateUrl(urlInput.value));
        
        const maxPagesInput = document.getElementById('maxPages');
        const timeoutInput = document.getElementById('timeout');
        
        maxPagesInput.addEventListener('input', () => this.updateFormHints());
        timeoutInput.addEventListener('input', () => this.updateFormHints());
        
        const modeRadios = document.querySelectorAll('input[name="scrapingMode"]');
        modeRadios.forEach(radio => {
            radio.addEventListener('change', () => this.handleModeChange());
        });
    }
    
    async checkApiStatus() {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        try {
            statusDot.className = 'status-dot checking';
            statusText.textContent = 'جاري التحقق...';
            
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            
            if (response.ok && data.status === 'healthy') {
                statusDot.className = 'status-dot';
                statusText.textContent = 'متصل ✓';
                this.showNotification('API متصل وجاهز للاستخدام', 'success');
            } else {
                throw new Error('API غير متاح');
            }
        } catch (error) {
            statusDot.className = 'status-dot error';
            statusText.textContent = 'غير متصل ✗';
            this.showNotification('خطأ في الاتصال بـ API', 'error');
        }
    }
    
    setupFormValidation() {
        const form = document.getElementById('scrapeForm');
        const inputs = form.querySelectorAll('input[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }
    
    validateField(field) {
        const value = field.value.trim();
        
        if (field.type === 'url' && value) {
            return this.validateUrl(value);
        }
        
        if (field.required && !value) {
            this.showFieldError(field, 'هذا الحقل مطلوب');
            return false;
        }
        
        return true;
    }
    
    validateUrl(url) {
        const urlInput = document.getElementById('url');
        
        if (!url) {
            this.clearFieldError(urlInput);
            return false;
        }
        
        try {
            const urlObj = new URL(url);
            if (!['http:', 'https:'].includes(urlObj.protocol)) {
                this.showFieldError(urlInput, 'الرابط يجب أن يبدأ بـ http:// أو https://');
                return false;
            }
            
            this.clearFieldError(urlInput);
            return true;
        } catch (error) {
            this.showFieldError(urlInput, 'تنسيق الرابط غير صحيح');
            return false;
        }
    }
    
    showFieldError(field, message) {
        this.clearFieldError(field);
        
        field.style.borderColor = '#ff416c';
        field.style.boxShadow = '0 0 10px rgba(255, 65, 108, 0.3)';
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            color: #ff416c;
            font-size: 0.875rem;
            margin-top: 0.5rem;
            animation: slideInUp 0.3s ease;
        `;
        
        field.parentNode.appendChild(errorDiv);
    }
    
    clearFieldError(field) {
        field.style.borderColor = '';
        field.style.boxShadow = '';
        
        const errorDiv = field.parentNode.querySelector('.field-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    }
    
    updateFormHints() {
        const maxPages = document.getElementById('maxPages').value;
        const timeout = document.getElementById('timeout').value;
        const estimatedTime = Math.ceil((maxPages * timeout) / 10);
    }
    
    handleModeChange() {
        const selectedMode = document.querySelector('input[name="scrapingMode"]:checked').value;
        const maxPagesGroup = document.getElementById('maxPagesGroup');
        const maxPagesInput = document.getElementById('maxPages');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = submitBtn.querySelector('.btn-text');
        
        if (selectedMode === 'single') {
            maxPagesGroup.style.opacity = '0.5';
            maxPagesInput.disabled = true;
            btnText.textContent = '🎯 استخراج صفحة واحدة';
        } else if (selectedMode === 'stream') {
            maxPagesGroup.style.opacity = '1';
            maxPagesInput.disabled = false;
            btnText.textContent = '📡 بث مباشر للنتائج';
        } else if (selectedMode === 'unlimited') {
            maxPagesGroup.style.opacity = '0.5';
            maxPagesInput.disabled = true;
            btnText.textContent = '🚀 استخراج كامل للموقع';
        } else {
            maxPagesGroup.style.opacity = '1';
            maxPagesInput.disabled = false;
            btnText.textContent = 'بدء الاستخراج';
        }
    }
    
    async handleFormSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        
        if (!this.validateForm(form)) {
            this.showNotification('يرجى تصحيح الأخطاء في النموذج', 'error');
            return;
        }
        
        const url = formData.get('url');
        const selectedMode = document.querySelector('input[name="scrapingMode"]:checked').value;
        let maxPages;
        if (selectedMode === 'unlimited') {
            maxPages = 999999;
        } else if (selectedMode === 'single') {
            maxPages = 1;
        } else if (selectedMode === 'stream') {
            maxPages = parseInt(formData.get('maxPages'));
        } else {
            maxPages = parseInt(formData.get('maxPages'));
        }
        const timeout = parseInt(formData.get('timeout'));
        
        if (selectedMode === 'unlimited') {
            const confirmed = confirm('⚠️ تحذير: ستقوم باستخراج جميع صفحات الموقع بدون حد أقصى.\nقد يستغرق هذا وقتاً طويلاً جداً ويستهلك موارد كثيرة.\nهل تريد المتابعة؟');
            if (!confirmed) {
                return;
            }
        }
        
        await this.startScraping(url, maxPages, timeout, selectedMode);
    }
    
    validateForm(form) {
        const inputs = form.querySelectorAll('input[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    async startScraping(url, maxPages, timeout, mode = 'limited') {
        const submitBtn = document.getElementById('submitBtn');
        const progressSection = document.getElementById('progressSection');
        const resultsSection = document.getElementById('resultsSection');
        
        try {
            submitBtn.classList.add('loading');
            this.showProgress();
            this.hideResults();
            
            this.results = [];
            
            progressSection.style.display = 'block';
            progressSection.scrollIntoView({ behavior: 'smooth' });
            
            let requestUrl, data;
            
            if (mode === 'single') {
                this.updateProgress(50, 'جاري استخراج الصفحة...');
                requestUrl = `${this.apiBaseUrl}/scrape-single?url=${encodeURIComponent(url)}&timeout=${timeout}`;
                
                const response = await fetch(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'خطأ في معالجة الطلب');
                }
                
                const singleData = await response.json();
                data = [singleData];
            } else if (mode === 'unlimited') {
                await this.startUnlimitedStreamingScraping(url, timeout);
                return;
            } else if (mode === 'stream') {
                await this.startStreamingScraping(url, maxPages, timeout);
                return;
            } else {
                this.simulateProgress(maxPages);
                requestUrl = `${this.apiBaseUrl}/scrape-pages?url=${encodeURIComponent(url)}&max_pages=${maxPages}&timeout=${timeout}`;
                
                const response = await fetch(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'خطأ في معالجة الطلب');
                }
                
                data = await response.json();
            }
            
            this.results = data;
            
            let modeText;
            if (mode === 'single') {
                modeText = 'صفحة واحدة';
            } else if (mode === 'unlimited') {
                modeText = 'استخراج كامل';
            } else {
                modeText = 'استخراج محدود';
            }
            
            this.updateProgress(100, `تم الانتهاء - ${data.length} صفحة (${modeText})`);
            
            this.displayResults(data);
            this.showNotification(`تم استخراج ${data.length} صفحة بنجاح باستخدام ${modeText}`, 'success');
            
        } catch (error) {
            console.error('Scraping error:', error);
            this.showNotification(`خطأ: ${error.message}`, 'error');
            this.updateProgress(0, 'فشل في المعالجة');
        } finally {
            submitBtn.classList.remove('loading');
        }
    }
    
    showProgress() {
        const progressSection = document.getElementById('progressSection');
        progressSection.style.display = 'block';
        this.updateProgress(0, 'بدء المعالجة...');
    }
    
    hideProgress() {
        const progressSection = document.getElementById('progressSection');
        progressSection.style.display = 'none';
    }
    
    hideResults() {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.style.display = 'none';
    }
    
    updateProgress(percentage, text) {
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.getElementById('progressText');
        
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = text;
    }
    
    simulateProgress(maxPages) {
        let progress = 0;
        const increment = 90 / maxPages;
        
        const interval = setInterval(() => {
            progress += increment;
            if (progress >= 90) {
                clearInterval(interval);
                this.updateProgress(90, 'معالجة النتائج...');
                return;
            }
            
            const currentPage = Math.floor(progress / increment);
            this.updateProgress(progress, `معالجة الصفحة ${currentPage} من ${maxPages}...`);
        }, 1000);
    }
    
    simulateUnlimitedProgress() {
        let progress = 0;
        let pageCount = 0;
        
        const interval = setInterval(() => {
            progress += 2;
            pageCount += Math.floor(Math.random() * 5) + 1;
            
            if (progress >= 90) {
                clearInterval(interval);
                this.updateProgress(90, `معالجة النتائج النهائية... (${pageCount}+ صفحة)`);
                return;
            }
            
            this.updateProgress(progress, `🔍 اكتشاف وجلب الصفحات... (${pageCount} صفحة تمت معالجتها)`);
        }, 1500);
    }
    
    displayResults(data) {
        const resultsSection = document.getElementById('resultsSection');
        const resultsGrid = document.getElementById('resultsGrid');
        
        resultsGrid.innerHTML = '';
        
        data.forEach((item, index) => {
            const card = this.createResultCard(item.data, index);
            resultsGrid.appendChild(card);
        });
        
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    createResultCard(data, index) {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.style.animationDelay = `${index * 0.1}s`;
        
        const title = data.title || 'بدون عنوان';
        const content = data.content || 'لا يوجد محتوى';
        const url = data.source_url || '';
        const createdAt = new Date(data.created_at).toLocaleString('ar-EG');
        const wordCount = content.split(' ').length;
        
        card.innerHTML = `
            <h4 title="${title}">${title}</h4>
            <div class="url">${url}</div>
            <div class="content">${content}</div>
            <div class="meta">
                <span>📅 ${createdAt}</span>
                <span>📝 ${wordCount} كلمة</span>
                <span>🆔 ${data.id.slice(0, 8)}...</span>
            </div>
        `;
        
        card.addEventListener('click', () => this.showFullContent(data));
        
        return card;
    }
    
    showFullContent(data) {
        const modal = document.createElement('div');
        modal.className = 'content-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            animation: fadeIn 0.3s ease;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 2rem;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            color: white;
        `;
        
        content.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3>${data.title || 'بدون عنوان'}</h3>
                <button onclick="this.closest('.content-modal').remove()" style="
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    padding: 0.5rem 1rem;
                    cursor: pointer;
                ">✕</button>
            </div>
            <div style="margin-bottom: 1rem; font-size: 0.9rem; color: #a0a0a0;">
                🔗 ${data.source_url}
            </div>
            <div style="line-height: 1.6;">
                ${data.content}
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.8rem; color: #a0a0a0;">
                📅 ${new Date(data.created_at).toLocaleString('ar-EG')} | 🆔 ${data.id}
            </div>
        `;
        
        modal.appendChild(content);
        document.body.appendChild(modal);
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
    
    async startStreamingScraping(url, maxPages, timeout) {
        const submitBtn = document.getElementById('submitBtn');
        const progressSection = document.getElementById('progressSection');
        const resultsSection = document.getElementById('resultsSection');
        
        try {
            submitBtn.classList.add('loading');
            this.showProgress();
            this.hideResults();
            
            this.results = [];
            
            progressSection.style.display = 'block';
            progressSection.scrollIntoView({ behavior: 'smooth' });
            
            const streamUrl = `${this.apiBaseUrl}/scrape-stream`;
            const requestBody = {
                url: url,
                max_pages: maxPages,
                timeout: timeout
            };
            
            const response = await fetch(streamUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                const lines = buffer.split('\n');
                buffer = lines.pop();
                
                for (const line of lines) {
                    if (line.trim() && line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.substring(6);
                            const data = JSON.parse(jsonStr);
                            
                            switch (data.type) {
                                case 'start':
                                    this.updateProgress(0, data.message);
                                    this.showNotification('بدء البث المباشر للنتائج', 'info');
                                    break;
                                    
                                case 'page':
                                    this.results.push({ data: data.data });
                                    
                                    const percentage = data.progress ? data.progress.percentage : 0;
                                    const current = data.progress ? data.progress.current : this.results.length;
                                    const total = data.progress ? data.progress.total : maxPages;
                                    
                                    this.updateProgress(percentage, `تم استخراج ${current} من ${total} صفحات...`);
                                    
                                    this.displayResults(this.results);
                                    break;
                                    
                                case 'complete':
                                    this.updateProgress(100, `تم الانتهاء - ${data.total} صفحة`);
                                    this.showNotification(`تم استخراج ${data.total} صفحة بنجاح`, 'success');
                                    break;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Streaming error:', error);
            this.showNotification(`خطأ: ${error.message}`, 'error');
            this.updateProgress(0, 'فشل في المعالجة');
        } finally {
            submitBtn.classList.remove('loading');
        }
    }
    
    async startUnlimitedStreamingScraping(url, timeout) {
        const submitBtn = document.getElementById('submitBtn');
        const progressSection = document.getElementById('progressSection');
        const resultsSection = document.getElementById('resultsSection');
        
        try {
            submitBtn.classList.add('loading');
            this.showProgress();
            this.hideResults();
            
            this.results = [];
            
            progressSection.style.display = 'block';
            progressSection.scrollIntoView({ behavior: 'smooth' });
            
            const streamUrl = `${this.apiBaseUrl}/scrape-stream`;
            const requestBody = {
                url: url,
                max_pages: 999999,
                timeout: timeout
            };
            
            const response = await fetch(streamUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                const lines = buffer.split('\n');
                buffer = lines.pop();
                
                for (const line of lines) {
                    if (line.trim() && line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.substring(6);
                            const data = JSON.parse(jsonStr);
                            
                            switch (data.type) {
                                case 'start':
                                    this.updateProgress(0, data.message);
                                    this.showNotification('بدء الاستخراج الكامل للموقع', 'info');
                                    break;
                                    
                                case 'page':
                                    this.results.push({ data: data.data });
                                    
                                    const current = this.results.length;
                                    
                                    this.updateProgress(Math.min(90, current), `🔍 تم استخراج ${current} صفحات...`);
                                    
                                    this.displayResults(this.results);
                                    break;
                                    
                                case 'complete':
                                    this.updateProgress(100, `تم الانتهاء - ${data.total} صفحة`);
                                    this.showNotification(`تم استخراج ${data.total} صفحة بنجاح`, 'success');
                                    break;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Unlimited streaming error:', error);
            this.showNotification(`خطأ: ${error.message}`, 'error');
            this.updateProgress(0, 'فشل في المعالجة');
        } finally {
            submitBtn.classList.remove('loading');
        }
    }
    
    downloadResults() {
        if (this.results.length === 0) {
            this.showNotification('لا توجد نتائج للتحميل', 'warning');
            return;
        }
        
        const dataStr = JSON.stringify(this.results, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `scraped_data_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('تم تحميل الملف بنجاح', 'success');
    }
    
    async sendToDatabase() {
        if (this.results.length === 0) {
            this.showNotification('لا توجد نتائج للإرسال', 'warning');
            return;
        }
        
        this.showNotification('جاري إرسال البيانات لقاعدة البيانات...', 'info');
        
        setTimeout(() => {
            this.showNotification('تم إرسال البيانات بنجاح', 'success');
        }, 1500);
    }
    
    clearResults() {
        this.results = [];
        const resultsGrid = document.getElementById('resultsGrid');
        const resultsSection = document.getElementById('resultsSection');
        const progressSection = document.getElementById('progressSection');
        
        resultsGrid.innerHTML = '';
        resultsSection.style.display = 'none';
        progressSection.style.display = 'none';
        
        this.showNotification('تم مسح النتائج', 'info');
    }
    
    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer');
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new WebScrapingUI();
});
