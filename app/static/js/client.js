// 客户端仪表板JavaScript

class ClientDashboard {
    constructor() {
        this.isTraining = false;
        this.uploadedFiles = [];
        this.trainingData = [];
        this.currentRound = 0;
        this.totalRounds = 0;
        this.socket = null; // SocketIO连接
        this.trainingId = null; // 当前训练ID
        
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.setupEventListeners();
        this.setupFileUpload();
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
    
    // 初始化SocketIO连接
    initializeSocket() {
        if (window.flSocket) {
            this.socket = window.flSocket;
            this.setupSocketListeners();
        }
    }
    
    // 设置Socket事件监听器
    setupSocketListeners() {
        if (!this.socket) return;
        
        // 监听加入训练事件
        this.socket.on('join_training', (data) => {
            this.handleJoinTraining(data);
        });
        
        // 监听连接状态
        this.socket.on('connect', () => {
            this.updateConnectionStatus('已连接', 'success');
        });
        
        this.socket.on('disconnect', () => {
            this.updateConnectionStatus('连接断开', 'error');
        });
    }
    
    // 处理加入训练事件
    handleJoinTraining(data) {
        this.trainingId = data.training_id;
        this.totalRounds = data.rounds;
        this.currentRound = 0;
        
        this.addLogEntry(`收到训练邀请 - 训练ID: ${data.training_id}, 轮数: ${data.rounds}`, 'info');
        this.startClientTraining();
    }
    
    // 开始客户端训练
    startClientTraining() {
        if (this.uploadedFiles.length === 0) {
            this.addLogEntry('没有训练数据，无法开始训练', 'warning');
            return;
        }
        
        this.isTraining = true;
        this.updateTrainingStatus('训练中');
        this.addLogEntry('开始本地训练...', 'info');
        
        // 开始训练轮次
        this.trainNextRound();
    }
    
    // 训练下一轮
    trainNextRound() {
        if (!this.isTraining || this.currentRound >= this.totalRounds) {
            this.completeTraining();
            return;
        }
        
        this.currentRound++;
        this.addLogEntry(`开始第 ${this.currentRound} 轮本地训练`, 'info');
        
        // 模拟训练过程
        const trainingDuration = Math.random() * 3000 + 2000; // 2-5秒
        
        setTimeout(() => {
            this.completeRound();
        }, trainingDuration);
    }
    
    // 完成当前轮次
    completeRound() {
        // 模拟训练结果
        const loss = Math.random() * 0.5 + 0.2; // 0.2-0.7
        const accuracy = Math.random() * 0.3 + 0.7; // 0.7-1.0
        
        this.addLogEntry(`第 ${this.currentRound} 轮完成 - Loss: ${loss.toFixed(4)}, Accuracy: ${(accuracy * 100).toFixed(2)}%`, 'success');
        
        // 通知服务器完成训练轮次
        if (this.socket && this.trainingId) {
            this.socket.emit('training_round_complete', {
                training_id: this.trainingId,
                round: this.currentRound,
                loss: loss,
                accuracy: accuracy
            });
        }
        
        // 继续下一轮或完成训练
        if (this.currentRound < this.totalRounds) {
            setTimeout(() => {
                this.trainNextRound();
            }, 1000); // 1秒后开始下一轮
        } else {
            this.completeTraining();
        }
    }
    
    // 完成训练
    completeTraining() {
        this.isTraining = false;
        this.updateTrainingStatus('训练完成');
        this.addLogEntry(`所有 ${this.totalRounds} 轮训练已完成`, 'success');
        
        // 重置训练相关变量
        this.trainingId = null;
        this.currentRound = 0;
        this.totalRounds = 0;
    }
    
    // 更新训练状态显示
    updateTrainingStatus(status) {
        const statusElement = document.getElementById('training-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `training-status ${this.isTraining ? 'active' : 'inactive'}`;
        }
    }
    
    // 更新连接状态
    updateConnectionStatus(text, status) {
        const statusText = document.getElementById('status-text');
        const statusIndicator = document.getElementById('connection-status');
        
        if (statusText) statusText.textContent = text || '连接中...';
        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${status || 'warning'}`;
        }
    }
    
    setupEventListeners() {
        // 更新参数按钮
        const updateParamsBtn = document.getElementById('update-parameters');
        if (updateParamsBtn) {
            updateParamsBtn.addEventListener('click', () => {
                this.updateParameters();
            });
        }
        
        // 清空日志
        const clearLogBtn = document.getElementById('clear-log');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => {
                this.clearLog();
            });
        }
        
        // 文件输入
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileSelect(e.target.files);
            });
        }
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
      async uploadSingleFile(file, index, total) {
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
                    
                    // 如果是最后一个文件，通知服务器
                    if (index === total) {
                        this.notifyDataUpload();
                    }
                    
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
        const updateBtn = document.getElementById('update-parameters');
        const hasFiles = this.uploadedFiles.length > 0;
        
        if (updateBtn) {
            updateBtn.disabled = !hasFiles || this.isTraining;
            
            if (hasFiles && !this.isTraining) {
                updateBtn.classList.remove('btn-secondary');
                updateBtn.classList.add('btn-success');
            } else {
                updateBtn.classList.remove('btn-success');
                updateBtn.classList.add('btn-secondary');
            }
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
      // 更新参数方法
    updateParameters() {
        if (this.uploadedFiles.length === 0) {
            this.addLogEntry('请先上传训练数据', 'warning');
            return;
        }

        // 启用/禁用按钮状态
        const updateBtn = document.getElementById('update-parameters');
        updateBtn.disabled = true;
        updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 更新中...';

        this.addLogEntry('开始更新模型参数...', 'info');
        this.notifyTrainingStatus('started', { current: 0, total: 1 });

        // 模拟参数更新过程
        setTimeout(() => {
            this.addLogEntry('正在与服务器同步参数...', 'info');
            
            // 通知服务器更新参数
            if (this.socket) {
                this.socket.emit('update_parameters', {
                    client_id: document.getElementById('client-id').textContent,
                    data_count: this.uploadedFiles.length,
                    timestamp: new Date().toISOString()
                });
            }

            setTimeout(() => {
                this.addLogEntry('模型参数更新完成', 'success');
                this.notifyTrainingStatus('completed', { current: 1, total: 1 });
                
                updateBtn.disabled = false;
                updateBtn.innerHTML = '<i class="fas fa-sync"></i> 更新参数';
                
                // 更新统计信息
                this.updateClientStats();
            }, 2000);
        }, 1500);
    }

    // 更新客户端统计信息
    updateClientStats() {
        const totalSessions = parseInt(document.getElementById('total-sessions').textContent) + 1;
        const completedSessions = parseInt(document.getElementById('completed-sessions').textContent) + 1;
        
        document.getElementById('total-sessions').textContent = totalSessions;
        document.getElementById('completed-sessions').textContent = completedSessions;
    }

    // 通知服务器数据上传状态
    notifyDataUpload() {
        if (this.socket && this.uploadedFiles.length > 0) {
            const clientId = document.getElementById('client-id').textContent;
            this.socket.emit('client_data_uploaded', {
                client_id: clientId,
                file_count: this.uploadedFiles.length
            });
        }
    }

    // 通知服务器训练状态变化
    notifyTrainingStatus(status, roundInfo = null) {
        if (this.socket) {
            const clientId = document.getElementById('client-id').textContent;
            this.socket.emit('training_status_change', {
                client_id: clientId,
                status: status,
                round_info: roundInfo
            });
        }
    }
}

// 全局客户端仪表板实例
let clientDash;

document.addEventListener('DOMContentLoaded', function() {
    clientDash = new ClientDashboard();
});