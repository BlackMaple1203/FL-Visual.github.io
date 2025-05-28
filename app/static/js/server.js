// 服务器端仪表板JavaScript

class ServerDashboard {    constructor() {
        this.connectedClients = [];
        this.nodes = new Map(); // 存储添加的节点
        this.trainingInProgress = false;
        this.currentRound = 0;
        this.totalRounds = 3;
        this.participatingClients = 1;
        this.socket = null;
        
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.setupEventListeners();
        this.loadNodes();
        this.loadServerLogs();
        this.updateClientStatus();
        this.addLogEntry('服务器已启动，等待添加节点...', 'info');
        
        // 定期更新状态
        setInterval(() => {
            this.updateClientStatus();
            this.loadServerLogs();
        }, 5000);
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
        
        this.socket.on('connect', () => {
            this.addLogEntry('SocketIO连接已建立', 'info');
        });
        
        this.socket.on('disconnect', () => {
            this.addLogEntry('SocketIO连接已断开', 'warning');
        });
    }
    
    setupEventListeners() {
        // 添加节点按钮
        const addNodeBtn = document.getElementById('add-node-btn');
        if (addNodeBtn) {
            addNodeBtn.addEventListener('click', () => {
                this.addNodeByClientId();
            });
        }
        
        // 客户端ID输入框回车事件
        const clientIdInput = document.getElementById('client-id-input');
        if (clientIdInput) {
            clientIdInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.addNodeByClientId();
                }
            });
        }
        
        // 开始训练按钮
        const startTrainingBtn = document.getElementById('start-training-btn');
        if (startTrainingBtn) {
            startTrainingBtn.addEventListener('click', () => {
                this.startGlobalTraining();
            });
        }
        
        // 停止训练按钮
        const stopTrainingBtn = document.getElementById('stop-training-btn');
        if (stopTrainingBtn) {
            stopTrainingBtn.addEventListener('click', () => {
                this.stopGlobalTraining();
            });
        }
        
        // 重置按钮
        const resetBtn = document.getElementById('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetSystem();
            });
        }
        
        // 参数调整按钮
        const roundPlus = document.getElementById('round-plus');
        const roundMinus = document.getElementById('round-minus');
        const clientPlus = document.getElementById('client-plus');
        const clientMinus = document.getElementById('client-minus');
        
        if (roundPlus) roundPlus.addEventListener('click', () => this.adjustRounds(1));
        if (roundMinus) roundMinus.addEventListener('click', () => this.adjustRounds(-1));
        if (clientPlus) clientPlus.addEventListener('click', () => this.adjustParticipatingClients(1));
        if (clientMinus) clientMinus.addEventListener('click', () => this.adjustParticipatingClients(-1));
        
        // 日志控制
        const clearLogBtn = document.getElementById('clear-log-btn');
        const clearServerLogsBtn = document.getElementById('clear-server-logs');
        
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => {
                this.clearLog();
            });
        }
        
        if (clearServerLogsBtn) {
            clearServerLogsBtn.addEventListener('click', () => {
                this.clearServerLogs();
            });
        }
    }
    
    // 通过客户端ID添加节点
    async addNodeByClientId() {
        const clientIdInput = document.getElementById('client-id-input');
        const clientId = clientIdInput.value.trim();
        
        if (!clientId) {
            this.showMessage('请输入客户端ID', 'error');
            return;
        }
        
        // 验证客户端ID格式
        if (!/^CLIENT_[A-Z0-9]{8}$/.test(clientId)) {
            this.showMessage('客户端ID格式错误，应为 CLIENT_XXXXXXXX', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/add_node', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ client_id: clientId })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage(result.message, 'success');
                this.addNodeToDisplay(clientId, result.username);
                clientIdInput.value = '';
                this.loadNodes(); // 重新加载节点状态
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            console.error('添加节点错误:', error);
            this.showMessage('添加节点失败: ' + error.message, 'error');
        }
    }
    
    // 在界面上添加节点显示
    addNodeToDisplay(clientId, username) {
        const nodesContainer = document.getElementById('nodes-container');
        if (!nodesContainer) return;
        
        // 检查节点是否已存在
        if (this.nodes.has(clientId)) {
            return;
        }
        
        const nodeElement = document.createElement('div');
        nodeElement.className = 'node client-node';
        nodeElement.id = `node-${clientId}`;
        nodeElement.innerHTML = `
            <div class="node-header">
                <span class="node-title">
                    <i class="fas fa-laptop"></i> ${username || clientId}
                </span>
                <button class="node-remove-btn" onclick="serverDash.removeNode('${clientId}')">×</button>
            </div>
            <div class="node-content">
                <div class="node-status" id="status-${clientId}">离线</div>
                <div class="node-data-status" id="data-${clientId}">
                    <i class="fas fa-times-circle text-danger"></i> 未上传数据
                </div>
                <div class="node-training-status" id="training-${clientId}">
                    <i class="fas fa-pause-circle text-secondary"></i> 待机中
                </div>
            </div>
        `;
        
        nodesContainer.appendChild(nodeElement);
        this.nodes.set(clientId, {
            element: nodeElement,
            username: username || clientId,
            status: 'offline',
            hasData: false,
            isTraining: false
        });
        
        this.addLogEntry(`添加了节点: ${clientId} (${username})`, 'info');
    }
    
    // 移除节点
    async removeNode(clientId) {
        if (confirm(`确定要移除节点 ${clientId} 吗？`)) {
            const nodeElement = document.getElementById(`node-${clientId}`);
            if (nodeElement) {
                nodeElement.remove();
            }
            this.nodes.delete(clientId);
            this.addLogEntry(`移除了节点: ${clientId}`, 'warning');
        }
    }
    
    // 开始全局训练
    async startGlobalTraining() {
        try {
            const response = await fetch('/api/start_training', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.trainingInProgress = true;
                this.updateTrainingControls();
                this.showMessage(result.message, 'success');
                this.addLogEntry(`训练已开始: ${result.message}`, 'success');
                
                // 更新中心节点状态
                this.updateCentralNodeStatus('训练中');
                
                // 更新有数据的节点状态为训练中
                this.updateNodesTrainingStatus();
                
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            console.error('开始训练错误:', error);
            this.showMessage('开始训练失败: ' + error.message, 'error');
        }
    }
    
    // 停止全局训练
    stopGlobalTraining() {
        this.trainingInProgress = false;
        this.updateTrainingControls();
        this.updateCentralNodeStatus('待机中');
        this.addLogEntry('训练已停止', 'warning');
        
        // 更新所有节点状态
        this.nodes.forEach((node, clientId) => {
            this.updateNodeTrainingStatus(clientId, false);
        });
    }
      // 重置系统
    resetSystem() {
        if (confirm('确定要重置系统吗？这将清除所有节点和日志。')) {
            // 清除所有节点
            this.nodes.clear();
            const nodesContainer = document.getElementById('nodes-container');
            if (nodesContainer) {
                nodesContainer.innerHTML = '';
            }
            
            // 重置状态
            this.trainingInProgress = false;
            this.updateTrainingControls();
            this.updateCentralNodeStatus('待机中');
            
            // 清除日志
            this.clearLog();
            this.clearServerLogs();
            
            this.addLogEntry('系统已重置', 'info');
        }
    }
    
    // 执行训练轮次
    async executeTrainingRound(round) {
        this.addLogEntry(`开始第 ${round}/${this.totalRounds} 轮训练`, 'info');
        
        // 选择参与的客户端
        const selectedClients = this.selectParticipatingClients();
        this.updateClientStatus(selectedClients, 'training');
        
        this.addLogEntry(`选择 ${selectedClients.length} 个客户端参与训练`, 'info');
        
        // 模拟客户端训练过程
        await this.simulateClientTraining(selectedClients);
        
        // 聚合模型参数
        await this.aggregateModels(selectedClients);
        
        // 生成并更新全局loss
        const globalLoss = this.generateGlobalLoss(round);
        this.updateGlobalLossChart(round, globalLoss);
        
        this.addLogEntry(`第 ${round} 轮训练完成，全局Loss: ${globalLoss.toFixed(4)}`, 'success');
        
        // 重置客户端状态
        this.updateClientStatus(selectedClients, 'online');
        
        // 等待下一轮
        if (round < this.totalRounds && this.trainingInProgress) {
            await this.delay(2000);
        }
    }
    
    selectParticipatingClients() {
        const availableClients = this.connectedClients.filter(client => client.status === 'online');
        const numToSelect = Math.min(this.participatingClients, availableClients.length);
        
        // 随机选择客户端
        const shuffled = [...availableClients].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, numToSelect);
    }
    
    async simulateClientTraining(clients) {
        const trainingPromises = clients.map(async (client, index) => {
            await this.delay(500 + index * 200); // 错开开始时间
            this.addLogEntry(`客户端 ${client.name} 开始本地训练`, 'info');
            
            // 模拟训练时间
            await this.delay(1500 + Math.random() * 1000);
            
            this.addLogEntry(`客户端 ${client.name} 完成本地训练`, 'success');
        });
        
        await Promise.all(trainingPromises);
    }
    
    async aggregateModels(clients) {
        this.addLogEntry('开始聚合客户端模型参数...', 'info');
        
        // 模拟参数聚合过程
        await this.delay(1000);
        
        this.addLogEntry('模型参数聚合完成', 'success');
        this.addLogEntry('向客户端分发更新的全局模型', 'info');
    }
    
    generateGlobalLoss(round) {
        // 生成递减的loss值，带有一些随机波动
        const baseLoss = 2.5;
        const decay = 0.85;
        const noise = (Math.random() - 0.5) * 0.15;
        return Math.max(0.1, baseLoss * Math.pow(decay, round - 1) + noise);
    }
    
    stopGlobalTraining() {
        this.trainingInProgress = false;
        this.updateTrainingControls();
        this.updateStatusDisplay('训练已停止');
        this.updateClientStatus(this.connectedClients, 'online');
        this.addLogEntry('联邦学习训练已停止', 'warning');
    }
    
    completeTraining() {
        this.trainingInProgress = false;
        this.updateTrainingControls();
        this.updateStatusDisplay('训练已完成');
        this.updateClientStatus(this.connectedClients, 'online');
        this.addLogEntry('联邦学习训练完成！', 'success');
    }
    
    resetSystem() {
        this.stopGlobalTraining();
        this.connectedClients = [];
        this.currentRound = 0;
        this.clearLog();
        this.resetGlobalLossChart();
        this.updateClientsDisplay();
        this.updateStatusDisplay('系统已重置，等待客户端连接...');
        this.addLogEntry('系统已重置', 'info');
    }
    
    // 更新训练控制按钮状态
    updateTrainingControls() {
        const startBtn = document.getElementById('start-training-btn');
        const stopBtn = document.getElementById('stop-training-btn');
        
        if (startBtn) startBtn.disabled = this.trainingInProgress;
        if (stopBtn) stopBtn.disabled = !this.trainingInProgress;
    }
    
    // 更新中心节点状态
    updateCentralNodeStatus(status) {
        const centralNode = document.querySelector('.central-node .node-status');
        if (centralNode) {
            centralNode.textContent = status;
            centralNode.className = `node-status ${status === '训练中' ? 'training' : 'idle'}`;
        }
    }
    
    // 更新节点训练状态
    updateNodeTrainingStatus(clientId, isTraining) {
        const trainingStatus = document.getElementById(`training-${clientId}`);
        if (trainingStatus) {
            if (isTraining) {
                trainingStatus.innerHTML = '<i class="fas fa-play-circle text-success"></i> 训练中';
            } else {
                trainingStatus.innerHTML = '<i class="fas fa-pause-circle text-secondary"></i> 待机中';
            }
        }
        
        // 更新内存中的节点状态
        if (this.nodes.has(clientId)) {
            this.nodes.get(clientId).isTraining = isTraining;
        }
    }
    
    // 更新所有节点训练状态
    updateNodesTrainingStatus() {
        this.nodes.forEach((node, clientId) => {
            if (node.hasData) {
                this.updateNodeTrainingStatus(clientId, true);
            }
        });
    }
    
    // 加载节点
    async loadNodes() {
        try {
            const response = await fetch('/api/server_nodes');
            if (response.ok) {
                const nodes = await response.json();
                
                // 清空现有节点显示
                const nodesContainer = document.getElementById('nodes-container');
                if (nodesContainer) {
                    nodesContainer.innerHTML = '';
                }
                this.nodes.clear();
                
                // 添加节点到显示
                nodes.forEach(node => {
                    this.addNodeToDisplay(node.client_id, node.username);
                });
            }
        } catch (error) {
            console.error('加载节点错误:', error);
        }
    }
    
    // 加载服务器日志
    async loadServerLogs() {
        try {
            const response = await fetch('/api/server_logs');
            if (response.ok) {
                const logs = await response.json();
                // 这里可以根据需要处理日志显示
            }
        } catch (error) {
            console.error('加载服务器日志错误:', error);
        }
    }
    
    // 更新客户端状态
    async updateClientStatus() {
        try {
            const response = await fetch('/api/client_status');
            if (response.ok) {
                const statuses = await response.json();
                
                // 更新节点状态显示
                this.nodes.forEach((node, clientId) => {
                    const clientStatus = statuses.find(s => s.client_id === clientId);
                    if (clientStatus) {
                        this.updateNodeStatus(clientId, clientStatus);
                    }
                });
            }
        } catch (error) {
            console.error('更新客户端状态错误:', error);
        }
    }
    
    // 更新单个节点状态
    updateNodeStatus(clientId, statusData) {
        const statusElement = document.getElementById(`status-${clientId}`);
        const dataElement = document.getElementById(`data-${clientId}`);
        
        if (statusElement) {
            const isOnline = statusData.is_online;
            statusElement.textContent = isOnline ? '在线' : '离线';
            statusElement.className = `node-status ${isOnline ? 'online' : 'offline'}`;
        }
        
        if (dataElement) {
            const hasData = statusData.has_uploaded_data;
            if (hasData) {
                dataElement.innerHTML = '<i class="fas fa-check-circle text-success"></i> 已上传数据';
            } else {
                dataElement.innerHTML = '<i class="fas fa-times-circle text-danger"></i> 未上传数据';
            }
        }
        
        // 更新内存中的节点状态
        if (this.nodes.has(clientId)) {
            const node = this.nodes.get(clientId);
            node.status = statusData.is_online ? 'online' : 'offline';
            node.hasData = statusData.has_uploaded_data;
        }
    }
    
    // 清除服务器日志
    async clearServerLogs() {
        try {
            const response = await fetch('/api/clear_server_logs', {
                method: 'POST'
            });
            
            if (response.ok) {
                this.addLogEntry('服务器日志已清空', 'info');
            }
        } catch (error) {
            console.error('清除服务器日志错误:', error);
        }
    }
    
    // 显示消息
    showMessage(message, type = 'info') {
        // 创建消息提示
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show`;
        messageDiv.style.position = 'fixed';
        messageDiv.style.top = '20px';
        messageDiv.style.right = '20px';
        messageDiv.style.zIndex = '9999';
        messageDiv.style.minWidth = '300px';
        
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(messageDiv);
        
        // 自动移除消息
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 5000);
    }
    
    // 调整训练轮数
    adjustRounds(delta) {
        const roundsDisplay = document.getElementById('rounds-value');
        if (roundsDisplay) {
            this.totalRounds = Math.max(1, Math.min(20, this.totalRounds + delta));
            roundsDisplay.textContent = this.totalRounds;
        }
    }
    
    // 调整参与客户端数量
    adjustParticipatingClients(delta) {
        const clientsDisplay = document.getElementById('clients-value');
        if (clientsDisplay) {
            const maxClients = this.nodes.size;
            this.participatingClients = Math.max(1, Math.min(maxClients, (this.participatingClients || 1) + delta));
            clientsDisplay.textContent = this.participatingClients;
        }
    }
    
    addLogEntry(message, type = 'info') {
        const logContent = document.getElementById('log-content');
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <span class="log-message ${type}">${message}</span>
        `;
        
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
        
        // 限制日志条目数量
        const entries = logContent.querySelectorAll('.log-entry');
        if (entries.length > 100) {
            entries[0].remove();
        }
    }
    
    clearLog() {
        const logContent = document.getElementById('log-content');
        logContent.innerHTML = '';
        this.addLogEntry('日志已清空', 'info');
    }
    
    toggleLogSize() {
        const messageLog = document.getElementById('message-log');
        const magnifyBtn = document.getElementById('magnify-log-btn');
        
        if (messageLog.style.height === '400px') {
            messageLog.style.height = '200px';
            magnifyBtn.innerHTML = '<i class="fas fa-expand"></i>';
            magnifyBtn.title = '放大显示';
        } else {
            messageLog.style.height = '400px';
            magnifyBtn.innerHTML = '<i class="fas fa-compress"></i>';
            magnifyBtn.title = '缩小显示';
        }
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 初始化服务器仪表板
let serverDash;
document.addEventListener('DOMContentLoaded', () => {
    serverDash = new ServerDashboard();
});