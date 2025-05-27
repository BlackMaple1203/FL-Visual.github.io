// 联邦学习过程模拟

// 全局变量
let globalModel = null;
let trainingComplete = false;
let currentRound = 0;
let totalRounds = 3;  // 默认训练轮数
let participatingClientsCount = 0; // 每轮参与的客户端数量，0表示全部参与
let shouldStopTraining = false;  // 新增：是否应该停止训练的标志

// 启动联邦学习过程
function startFederatedLearning(rounds = 3, clientCount = 0) {
    // 设置训练参数
    totalRounds = rounds;
    participatingClientsCount = clientCount;
    shouldStopTraining = false;  // 重置停止标志
    
    // 重置状态
    globalModel = {
        version: 0,
        accuracy: 0,
        parameters: {}
    };
    
    trainingComplete = false;
    currentRound = 0;
    
    // 开始第一轮训练
    trainNextRound();
}

// 停止联邦学习过程
function stopFederatedLearning() {
    shouldStopTraining = true;
}

// 训练下一轮
function trainNextRound() {
    // 检查是否应该停止训练
    if (shouldStopTraining) {
        handleTrainingStop();
        return;
    }
    
    currentRound++;
    
    if (currentRound > totalRounds) {
        completeTraining();
        return;
    }
    
    window.federatedUI.addLogMessage(`开始第 ${currentRound}/${totalRounds} 轮训练`, 'highlight');
    
    // 获取所有节点
    let nodeElements = Array.from(document.querySelectorAll('.client-node'));
    if (!nodeElements.length) return;
    
    // 如果设置了参与客户端数量且不是0（全部参与）
    if (participatingClientsCount > 0 && participatingClientsCount < nodeElements.length) {
        // 随机选择指定数量的客户端参与训练
        shuffleArray(nodeElements);
        nodeElements = nodeElements.slice(0, participatingClientsCount);
        
        // 记录本轮参与的节点ID
        const participatingNodeIds = nodeElements.map(el => parseInt(el.id.split('-')[1])).join(', ');
        window.federatedUI.addLogMessage(`本轮选择的参与节点: ${participatingNodeIds}`);
    }
    
    // 更新中央节点状态
    window.federatedUI.updateCentralNodeStatus('distributing', `正在向节点分发全局模型 (版本 ${globalModel.version})`);
    
    // 依次训练每个节点
    trainNodesSequentially(nodeElements, 0);
}

// 打乱数组顺序（Fisher-Yates洗牌算法）
function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}

// 依次训练每个节点
function trainNodesSequentially(nodeElements, index) {
    // 检查是否应该停止训练
    if (shouldStopTraining) {
        handleTrainingStop();
        return;
    }
    
    if (index >= nodeElements.length) {
        // 所有节点都已训练完成，开始聚合模型
        aggregateModels();
        return;
    }
    
    const nodeElement = nodeElements[index];
    const nodeId = parseInt(nodeElement.id.split('-')[1]);
    
    // 模拟分发全局模型
    setTimeout(() => {
        window.federatedUI.addLogMessage(`节点 ${nodeId} 接收全局模型`);
        
        // 开始本地训练
        trainNode(nodeId, () => {
            // 训练完成后，继续下一个节点
            trainNodesSequentially(nodeElements, index + 1);
        });
    }, 1000);
}

// 训练单个节点
function trainNode(nodeId, callback) {
    // 更新节点状态为训练中
    window.federatedUI.updateNodeStatus(nodeId, 'training', `节点 ${nodeId} 开始本地训练`);
    
    // 模拟训练过程 (2-4秒)
    const trainingTime = 2000 + Math.random() * 2000;
    
    setTimeout(() => {
        window.federatedUI.addLogMessage(`节点 ${nodeId} 完成本地训练，准备率: ${(80 + Math.random() * 15).toFixed(2)}%`);
        
        // 更新节点状态为上传中
        window.federatedUI.updateNodeStatus(nodeId, 'uploading', `节点 ${nodeId} 正在上传模型参数`);
        
        // 模拟上传过程 (1-2秒)
        const uploadTime = 1000 + Math.random() * 1000;
        
        setTimeout(() => {
            // 更新节点状态为完成
            window.federatedUI.updateNodeStatus(nodeId, 'complete', `节点 ${nodeId} 已上传模型参数`);
            callback();
        }, uploadTime);
    }, trainingTime);
}

// 聚合模型
function aggregateModels() {
    // 检查是否应该停止训练
    if (shouldStopTraining) {
        handleTrainingStop();
        return;
    }
    
    window.federatedUI.updateCentralNodeStatus('aggregating', "中央服务器正在聚合所有节点模型参数");
    
    // 模拟聚合过程 (3秒)
    setTimeout(() => {
        // 更新全局模型版本和精度
        globalModel.version++;
        globalModel.accuracy = Math.min(90 + (currentRound * 3) + (Math.random() * 2), 99);
        
        window.federatedUI.addLogMessage(`全局模型聚合完成，版本 ${globalModel.version}，准确率: ${globalModel.accuracy.toFixed(2)}%`, 'highlight');
        
        // 判断是否继续训练
        if (currentRound < totalRounds) {
            // 开始下一轮
            setTimeout(trainNextRound, 1500);
        } else {
            // 训练完成
            completeTraining();
        }
    }, 3000);
}

// 完成训练
function completeTraining() {
    window.federatedUI.updateCentralNodeStatus('complete', "联邦学习训练完成！");
    
    // 更新节点状态
    const nodes = document.querySelectorAll('.client-node');
    nodes.forEach(nodeElement => {
        const nodeId = parseInt(nodeElement.id.split('-')[1]);
        window.federatedUI.updateNodeStatus(nodeId, 'complete');
    });
    
    window.federatedUI.addLogMessage(`最终模型准确率: ${globalModel.accuracy.toFixed(2)}%`, 'highlight');
    window.federatedUI.addLogMessage('联邦学习训练完成 ✅', 'highlight');
    
    trainingComplete = true;
    window.federatedUI.finishTraining();
}

// 处理训练停止
function handleTrainingStop() {
    window.federatedUI.addLogMessage(`训练已在第 ${currentRound}/${totalRounds} 轮被用户停止`, 'warning');
    
    // 更新所有节点状态
    const nodes = document.querySelectorAll('.client-node');
    nodes.forEach(nodeElement => {
        const nodeId = parseInt(nodeElement.id.split('-')[1]);
        window.federatedUI.updateNodeStatus(nodeId, 'idle', null);
    });
    
    // 更新中心节点状态
    window.federatedUI.updateCentralNodeStatus('idle', "训练已停止");
    
    // 结束训练（不添加完成日志）
    window.federatedUI.finishTraining();
}

// 将函数暴露给全局作用域
window.startFederatedLearning = startFederatedLearning;
window.stopFederatedLearning = stopFederatedLearning;  // 新增：暴露停止函数
