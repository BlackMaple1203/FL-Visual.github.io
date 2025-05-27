// 服务器端仪表板JavaScript

class ServerDashboard {
    constructor() {
        this.connectedClients = [];
        this.globalLossChart = null;
        this.trainingInProgress = false;
        this.currentRound = 0;
        this.totalRounds = 3;
        this.participatingClients = 0;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initGlobalLossChart();
        this.loadConnectedClients();
        this.addLogEntry('服务器已启动，等待客户端连接...', 'info');
    }
    
    setupEventListeners() {
        // 训练控制按钮
        document.getElementById('start-training-btn').addEventListener('click', () => {
            this.startGlobalTraining();
        });
        
        document.getElementById('stop-training-btn').addEventListener('click', () => {
            this.stopGlobalTraining();
        });
        
        document.getElementById('reset-btn').addEventListener('click', () => {
            this.resetSystem();
        });
        
        // 参数调整按钮
        document.getElementById('round-plus').addEventListener('click', () => {
            this.adjustRounds(1);
        });
        
        document.getElementById('round-minus').addEventListener('click', () => {
            this.adjustRounds(-1);
        });
        
        document.getElementById('client-plus').addEventListener('click', () => {
            this.adjustParticipatingClients(1);
        });
        
        document.getElementById('client-minus').addEventListener('click', () => {
            this.adjustParticipatingClients(-1);
        });
        
        // 添加节点按钮（用于演示）
        document.getElementById('add-node-btn').addEventListener('click', () => {
            this.addDemoClient();
        });
        
        // 日志控制
        document.getElementById('clear-log-btn').addEventListener('click', () => {
            this.clearLog();
        });
        
        document.getElementById('magnify-log-btn').addEventListener('click', () => {
            this.toggleLogSize();
        });
    }
    
    adjustRounds(delta) {
        const input = document.getElementById('round-number');
        let value = parseInt(input.value) + delta;
        value = Math.max(1, Math.min(10, value));
        input.value = value;
        this.totalRounds = value;
    }
    
    adjustParticipatingClients(delta) {
        const input = document.getElementById('client-number');
        let value = parseInt(input.value) + delta;
        value = Math.max(0, Math.min(8, value));
        input.value = value;
        this.participatingClients = value;
    }
    
    async startGlobalTraining() {
        if (this.connectedClients.length === 0) {
            this.addLogEntry('没有连接的客户端，无法开始训练', 'warning');
            return;
        }
        
        this.trainingInProgress = true;
        this.updateTrainingControls();
        this.updateStatusDisplay('正在进行联邦学习训练...');
        
        this.totalRounds = parseInt(document.getElementById('round-number').value);
        this.participatingClients = parseInt(document.getElementById('client-number').value);
        
        if (this.participatingClients === 0) {
            this.participatingClients = this.connectedClients.length;
        }
        
        this.addLogEntry(`开始联邦学习训练，共 ${this.totalRounds} 轮`, 'success');
        this.addLogEntry(`参与训练的客户端数量: ${this.participatingClients}`, 'info');
        
        // 开始训练轮次
        for (let round = 1; round <= this.totalRounds; round++) {
            if (!this.trainingInProgress) break;
            
            this.currentRound = round;
            await this.executeTrainingRound(round);
        }
        
        if (this.trainingInProgress) {
            this.completeTraining();
        }
    }
    
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
    
    updateTrainingControls() {
        const startBtn = document.getElementById('start-training-btn');
        const stopBtn = document.getElementById('stop-training-btn');
        
        startBtn.disabled = this.trainingInProgress;
        stopBtn.disabled = !this.trainingInProgress;
    }
    
    updateStatusDisplay(message) {
        const statusDisplay = document.getElementById('status-display');
        statusDisplay.innerHTML = `<p>${message}</p>`;
    }
    
    updateClientStatus(clients, status) {
        clients.forEach(client => {
            client.status = status;
        });
        this.updateClientsDisplay();
    }
    
    loadConnectedClients() {
        // 模拟一些已连接的客户端
        const demoClients = [
            { id: 1, name: '客户端-001', status: 'online', lastSeen: new Date() },
            { id: 2, name: '客户端-002', status: 'online', lastSeen: new Date() },
            { id: 3, name: '客户端-003', status: 'online', lastSeen: new Date() }
        ];
        
        this.connectedClients = demoClients;
        this.updateClientsDisplay();
        
        setTimeout(() => {
            this.addLogEntry(`${demoClients.length} 个客户端已连接`, 'success');
        }, 1000);
    }
    
    addDemoClient() {
        const newClientId = this.connectedClients.length + 1;
        const newClient = {
            id: newClientId,
            name: `客户端-${String(newClientId).padStart(3, '0')}`,
            status: 'online',
            lastSeen: new Date()
        };
        
        this.connectedClients.push(newClient);
        this.updateClientsDisplay();
        this.addLogEntry(`新客户端 ${newClient.name} 已连接`, 'success');
    }
    
    updateClientsDisplay() {
        const clientsList = document.getElementById('clients-list');
        clientsList.innerHTML = '';
        
        if (this.connectedClients.length === 0) {
            clientsList.innerHTML = '<div class="text-muted text-center py-3">暂无连接的客户端</div>';
            return;
        }
        
        this.connectedClients.forEach(client => {
            const clientItem = document.createElement('div');
            clientItem.className = 'client-item';
            clientItem.innerHTML = `
                <div class="client-info">
                    <div class="client-name">
                        <i class="fas fa-laptop"></i> ${client.name}
                    </div>
                    <div class="client-last-seen">
                        最后活动: ${client.lastSeen.toLocaleTimeString()}
                    </div>
                </div>
                <div class="client-status ${client.status}">
                    ${this.getStatusText(client.status)}
                </div>
            `;
            clientsList.appendChild(clientItem);
        });
    }
    
    getStatusText(status) {
        const statusMap = {
            'online': '在线',
            'training': '训练中',
            'offline': '离线'
        };
        return statusMap[status] || status;
    }
    
    initGlobalLossChart() {
        const ctx = document.getElementById('global-loss-chart').getContext('2d');
        this.globalLossChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '全局Loss',
                    data: [],
                    borderColor: '#4a6fa5',
                    backgroundColor: 'rgba(74, 111, 165, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#4a6fa5',
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
                                size: 12,
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
                                size: 12,
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
                                size: 12,
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
                }
            }
        });
    }
    
    updateGlobalLossChart(round, loss) {
        if (!this.globalLossChart) return;
        
        this.globalLossChart.data.labels.push(`Round ${round}`);
        this.globalLossChart.data.datasets[0].data.push(loss);
        this.globalLossChart.update('active');
    }
    
    resetGlobalLossChart() {
        if (!this.globalLossChart) return;
        
        this.globalLossChart.data.labels = [];
        this.globalLossChart.data.datasets[0].data = [];
        this.globalLossChart.update();
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
document.addEventListener('DOMContentLoaded', () => {
    new ServerDashboard();
});