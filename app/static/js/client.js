// 客户端仪表板JavaScript

class ClientDashboard {
    constructor() {
        this.isTraining = false;
        this.uploadedFiles = [];
        this.lossChart = null;
        this.trainingData = [];
        this.currentRound = 0;
        this.totalRounds = 0;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupFileUpload();
        this.initLossChart();
        this.updateConnectionStatus();
        this.addLogEntry('客户端已启动，等待训练指令...', 'info');
        
        // 加载增强功能数据
        this.loadClientStats();
        this.loadServerInfo();
        this.loadModelPerformance();
        this.loadTrainingParams();
        
        // 定期更新数据
        setInterval(() => {
            this.loadClientStats();
            this.loadServerInfo();
        }, 30000); // 每30秒更新一次
    }
    
    setupEventListeners() {
        // 训练控制按钮
        document.getElementById('start-training').addEventListener('click', () => {
            this.startTraining();
        });
        
        document.getElementById('stop-training').addEventListener('click', () => {
            this.stopTraining();
        });
        
        // 清空日志
        document.getElementById('clear-log').addEventListener('click', () => {
            this.clearLog();
        });
        
        // 文件输入
        document.getElementById('file-input').addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });
    }
    
    setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        
        // 拖拽上传
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files);
        });
        
        // 点击上传
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
    }
    
    handleFileSelect(files) {
        const validFiles = [];
        
        for (let file of files) {
            if (file.name.endsWith('.nii.gz') || file.name.endsWith('.gz')) {
                validFiles.push(file);
            } else {
                this.addLogEntry(`文件 ${file.name} 格式不支持，请上传 .nii.gz 文件`, 'warning');
            }
        }
        
        if (validFiles.length > 0) {
            this.uploadFiles(validFiles);
        }
    }
    
    async uploadFiles(files) {
        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        modal.show();
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            await this.uploadSingleFile(file, i + 1, files.length);
        }
        
        modal.hide();
        this.updateUploadedFilesList();
        this.updateTrainingButtonState();
    }
    
    uploadSingleFile(file, index, total) {
        return new Promise((resolve) => {
            const progressBar = document.getElementById('upload-progress');
            const statusDiv = document.getElementById('upload-status');
            
            statusDiv.textContent = `上传文件 ${index}/${total}: ${file.name}`;
            
            // 模拟上传进度
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 20;
                if (progress > 100) progress = 100;
                
                progressBar.style.width = progress + '%';
                
                if (progress >= 100) {
                    clearInterval(interval);
                    
                    // 添加到已上传文件列表
                    this.uploadedFiles.push({
                        name: file.name,
                        size: this.formatFileSize(file.size),
                        status: 'uploaded',
                        file: file
                    });
                    
                    this.addLogEntry(`文件 ${file.name} 上传成功`, 'success');
                    
                    setTimeout(resolve, 500);
                }
            }, 100);
        });
    }
    
    updateUploadedFilesList() {
        const filesList = document.getElementById('files-list');
        const uploadedFilesDiv = document.getElementById('uploaded-files');
        
        if (this.uploadedFiles.length === 0) {
            uploadedFilesDiv.classList.remove('show');
            return;
        }
        
        uploadedFilesDiv.classList.add('show');
        filesList.innerHTML = '';
        
        this.uploadedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item fade-in-up';
            fileItem.innerHTML = `
                <div class="file-info">
                    <div class="file-icon">
                        <i class="fas fa-file-medical"></i>
                    </div>
                    <div class="file-details">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${file.size}</div>
                    </div>
                </div>
                <div class="file-status ${file.status}">${this.getStatusText(file.status)}</div>
            `;
            filesList.appendChild(fileItem);
        });
    }
    
    getStatusText(status) {
        const statusMap = {
            'uploaded': '已上传',
            'uploading': '上传中',
            'error': '上传失败'
        };
        return statusMap[status] || status;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    updateTrainingButtonState() {
        const startBtn = document.getElementById('start-training');
        const hasFiles = this.uploadedFiles.length > 0;
        
        startBtn.disabled = !hasFiles || this.isTraining;
        
        if (hasFiles && !this.isTraining) {
            startBtn.classList.remove('btn-secondary');
            startBtn.classList.add('btn-success');
        } else {
            startBtn.classList.remove('btn-success');
            startBtn.classList.add('btn-secondary');
        }
    }
    
    async startTraining() {
        if (this.uploadedFiles.length === 0) {
            this.addLogEntry('请先上传训练文件', 'warning');
            return;
        }
        
        this.isTraining = true;
        this.updateTrainingButtonState();
        this.updateTrainingStatus('training', '训练中');
        
        document.getElementById('start-training').disabled = true;
        document.getElementById('stop-training').disabled = false;
        
        this.addLogEntry('开始联邦学习训练...', 'info');
        
        try {
            // 模拟向服务器发送训练请求
            const response = await this.sendTrainingRequest();
            
            if (response.success) {
                this.totalRounds = response.rounds || 5;
                this.currentRound = 0;
                this.addLogEntry(`训练任务已创建，共 ${this.totalRounds} 轮`, 'success');
                this.simulateTraining();
            } else {
                throw new Error(response.message || '训练启动失败');
            }
        } catch (error) {
            this.addLogEntry(`训练启动失败: ${error.message}`, 'error');
            this.stopTraining();
        }
    }
    
    async sendTrainingRequest() {
        // 模拟API调用
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    success: true,
                    rounds: 5,
                    session_id: 'session_' + Date.now()
                });
            }, 1000);
        });
    }
    
    simulateTraining() {
        const roundInterval = setInterval(() => {
            if (!this.isTraining) {
                clearInterval(roundInterval);
                return;
            }
            
            this.currentRound++;
            this.addLogEntry(`开始第 ${this.currentRound}/${this.totalRounds} 轮训练`, 'info');
            
            // 模拟训练过程
            this.simulateRoundTraining();
            
            if (this.currentRound >= this.totalRounds) {
                clearInterval(roundInterval);
                this.completeTraining();
            }
        }, 3000);
    }
    
    simulateRoundTraining() {
        // 生成模拟loss数据
        const baseLoss = 2.5;
        const decay = 0.8;
        const noise = (Math.random() - 0.5) * 0.2;
        const loss = baseLoss * Math.pow(decay, this.currentRound - 1) + noise;
        
        this.trainingData.push({
            round: this.currentRound,
            loss: Math.max(0.1, loss)
        });
        
        this.updateLossChart();
        this.updateTrainingProgress();
        
        this.addLogEntry(`第 ${this.currentRound} 轮训练完成，Loss: ${loss.toFixed(4)}`, 'success');
    }
    
    updateTrainingProgress() {
        document.getElementById('current-round').textContent = `${this.currentRound}/${this.totalRounds}`;
    }
    
    completeTraining() {
        this.isTraining = false;
        this.updateTrainingButtonState();
        this.updateTrainingStatus('completed', '训练完成');
        
        document.getElementById('start-training').disabled = false;
        document.getElementById('stop-training').disabled = true;
        
        this.addLogEntry('联邦学习训练完成！', 'success');
        this.generatePredictionResults();
    }
    
    stopTraining() {
        this.isTraining = false;
        this.updateTrainingButtonState();
        this.updateTrainingStatus('stopped', '已停止');
        
        document.getElementById('start-training').disabled = false;
        document.getElementById('stop-training').disabled = true;
        
        this.addLogEntry('训练已停止', 'warning');
    }
    
    updateTrainingStatus(status, text) {
        const statusElement = document.getElementById('training-status');
        statusElement.textContent = text;
        statusElement.className = 'badge';
        
        switch (status) {
            case 'training':
                statusElement.classList.add('bg-warning');
                break;
            case 'completed':
                statusElement.classList.add('bg-success');
                break;
            case 'stopped':
                statusElement.classList.add('bg-danger');
                break;
            default:
                statusElement.classList.add('bg-secondary');
        }
    }
    
    initLossChart() {
        const ctx = document.getElementById('loss-chart').getContext('2d');
        this.lossChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Training Loss',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '训练轮次',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Loss',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    point: {
                        hoverRadius: 8
                    }
                }
            }
        });
    }
    
    updateLossChart() {
        if (!this.lossChart) return;
        
        const labels = this.trainingData.map(d => `Round ${d.round}`);
        const data = this.trainingData.map(d => d.loss);
        
        this.lossChart.data.labels = labels;
        this.lossChart.data.datasets[0].data = data;
        this.lossChart.update('active');
        
        // 隐藏"无数据"消息
        document.getElementById('no-data-message').style.display = 'none';
    }
    
    generatePredictionResults() {
        const resultsContainer = document.getElementById('prediction-results');
        resultsContainer.innerHTML = '';
        
        this.uploadedFiles.forEach((file, index) => {
            const confidence = 0.7 + Math.random() * 0.25; // 70-95%的置信度
            const prediction = this.generateRandomPrediction(confidence);
            
            const resultItem = document.createElement('div');
            resultItem.className = 'prediction-item fade-in-up';
            resultItem.innerHTML = `
                <div class="prediction-image">
                    <div style="width: 100%; height: 100%; background: linear-gradient(45deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-size: 2rem;">
                        <i class="fas fa-brain"></i>
                    </div>
                </div>
                <div class="prediction-details">
                    <div class="prediction-filename">${file.name}</div>
                    <div class="prediction-confidence ${this.getConfidenceClass(confidence)}">
                        置信度: ${(confidence * 100).toFixed(1)}%
                    </div>
                    <div class="prediction-description">
                        ${prediction.description}
                    </div>
                </div>
            `;
            
            resultsContainer.appendChild(resultItem);
        });
    }
    
    generateRandomPrediction(confidence) {
        const predictions = [
            {
                description: '模型检测到疑似病灶区域，建议进一步医学检查确认。'
            },
            {
                description: '未检测到明显异常，图像显示正常。'
            },
            {
                description: '检测到轻微异常信号，需要专业医生评估。'
            }
        ];
        
        return predictions[Math.floor(Math.random() * predictions.length)];
    }
    
    getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'confidence-high';
        if (confidence >= 0.6) return 'confidence-medium';
        return 'confidence-low';
    }
      updateConnectionStatus() {
        const statusIndicator = document.getElementById('connection-status');
        const statusText = document.getElementById('status-text');
        
        if (!statusIndicator || !statusText) {
            console.warn('连接状态元素未找到');
            return;
        }
        
        // 模拟连接状态
        setTimeout(() => {
            try {
                statusIndicator.className = 'status-indicator connected';
                statusText.textContent = '已连接到服务器';
                this.addLogEntry('成功连接到联邦学习服务器', 'success');
            } catch (error) {
                console.error('更新连接状态时出错:', error);
            }
        }, 2000);
    }
    
    addLogEntry(message, type = 'info') {
        const logContainer = document.getElementById('training-log');
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span class="message ${type}">${message}</span>
        `;
        
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    clearLog() {
        const logContainer = document.getElementById('training-log');
        logContainer.innerHTML = '';
        this.addLogEntry('日志已清空', 'info');
    }
    
    async loadClientStats() {
        try {
            const response = await fetch('/client_stats');
            if (response.ok) {
                const stats = await response.json();
                this.updateStatsDisplay(stats);
                this.updateRecentSessions(stats.recent_sessions);
            }
        } catch (error) {
            console.error('加载客户端统计失败:', error);
        }
    }
    
    async loadServerInfo() {
        try {
            const response = await fetch('/server_info');
            if (response.ok) {
                const info = await response.json();
                this.updateServerInfo(info);
            }
        } catch (error) {
            console.error('加载服务器信息失败:', error);
        }
    }
    
    async loadModelPerformance() {
        try {
            const response = await fetch('/model_performance');
            if (response.ok) {
                const data = await response.json();
                this.updatePerformanceCharts(data);
            }
        } catch (error) {
            console.error('加载模型性能数据失败:', error);
        }
    }
    
    updateStatsDisplay(stats) {
        document.getElementById('total-sessions').textContent = stats.total_sessions;
        document.getElementById('completed-sessions').textContent = stats.completed_sessions;
    }
    
    updateServerInfo(info) {
        document.getElementById('server-status').textContent = info.server_status === 'online' ? '在线' : '离线';
        document.getElementById('server-status').className = `badge bg-${info.server_status === 'online' ? 'success' : 'danger'}`;
        document.getElementById('server-round').textContent = `${info.current_round}/${info.total_rounds}`;
        document.getElementById('connected-clients').textContent = info.connected_clients;
        document.getElementById('model-accuracy').textContent = `${(info.model_accuracy * 100).toFixed(1)}%`;
    }
    
    updateRecentSessions(sessions) {
        const container = document.getElementById('recent-sessions');
        if (!container) return;
        
        if (sessions.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">暂无训练记录</p>';
            return;
        }
        
        container.innerHTML = sessions.map(session => `
            <div class="session-item">
                <div class="session-info">
                    <div class="session-filename">${session.filename}</div>
                    <div class="session-time">${new Date(session.created_at).toLocaleString()}</div>
                </div>
                <span class="session-status badge bg-${this.getStatusColor(session.status)}">${this.getStatusText(session.status)}</span>
            </div>
        `).join('');
    }
    
    updatePerformanceCharts(data) {
        this.createAccuracyChart(data);
        this.createLossChart(data);
    }
    
    createAccuracyChart(data) {
        const ctx = document.getElementById('accuracy-chart');
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.rounds,
                datasets: [{
                    label: '准确率',
                    data: data.accuracy,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        ticks: {
                            callback: function(value) {
                                return (value * 100).toFixed(0) + '%';
                            }
                        }
                    }
                }
            }
        });
    }
    
    createLossChart(data) {
        const ctx = document.getElementById('loss-chart');
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.rounds,
                datasets: [{
                    label: '损失',
                    data: data.loss,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    getStatusColor(status) {
        const colors = {
            'completed': 'success',
            'running': 'primary',
            'pending': 'warning',
            'failed': 'danger'
        };
        return colors[status] || 'secondary';
    }
    
    getStatusText(status) {
        const texts = {
            'completed': '已完成',
            'running': '运行中',
            'pending': '等待中',
            'failed': '失败'
        };
        return texts[status] || status;
    }
    
    refreshCharts() {
        this.loadModelPerformance();
        this.addLogEntry('图表已刷新', 'info');
    }
    
    saveTrainingParams() {
        const params = {
            learningRate: document.getElementById('learning-rate').value,
            batchSize: document.getElementById('batch-size').value,
            epochs: document.getElementById('epochs').value,
            optimizer: document.getElementById('optimizer').value
        };
        
        localStorage.setItem('fl_training_params', JSON.stringify(params));
        this.addLogEntry('训练参数已保存', 'success');
    }
    
    loadTrainingParams() {
        const savedParams = localStorage.getItem('fl_training_params');
        if (savedParams) {
            const params = JSON.parse(savedParams);
            document.getElementById('learning-rate').value = params.learningRate || 0.001;
            document.getElementById('batch-size').value = params.batchSize || 32;
            document.getElementById('epochs').value = params.epochs || 10;
            document.getElementById('optimizer').value = params.optimizer || 'adam';
        }
    }
    
    exportTrainingData() {
        this.addLogEntry('开始导出训练数据...', 'info');
        // 模拟导出过程
        setTimeout(() => {
            this.addLogEntry('训练数据导出完成', 'success');
        }, 2000);
    }
    
    downloadBestModel() {
        this.addLogEntry('准备下载最佳模型...', 'info');
        // 模拟下载过程
        setTimeout(() => {
            this.addLogEntry('模型下载完成', 'success');
        }, 1500);
    }
    
    generateReport() {
        this.addLogEntry('正在生成训练报告...', 'info');
        // 模拟报告生成
        setTimeout(() => {
            this.addLogEntry('训练报告生成完成', 'success');
        }, 3000);
    }
}

// 全局客户端仪表板实例
let clientDash;

document.addEventListener('DOMContentLoaded', function() {
    clientDash = new ClientDashboard();
});