#!/usr/bin/env node

const https = require('https');
const fs = require('fs');
const path = require('path');

// 尝试从多个来源获取 API Key
function getApiKey() {
  // 1. 环境变量优先
  if (process.env.DASHSCOPE_API_KEY) {
    return process.env.DASHSCOPE_API_KEY;
  }
  
  // 2. 从配置文件读取
  const configPath = path.join(__dirname, '.qwen-env');
  if (fs.existsSync(configPath)) {
    const content = fs.readFileSync(configPath, 'utf8');
    const match = content.match(/DASHSCOPE_API_KEY=(.+)/);
    if (match && match[1] && !match[1].includes('YOUR_API_KEY_HERE')) {
      return match[1].trim();
    }
  }
  
  return null;
}

const API_KEY = getApiKey();

// 阿里百炼 API 端点
const API_URL = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation';

if (!API_KEY) {
  console.error('❌ 错误：未找到 API Key');
  console.error('');
  console.error('请按以下任一方式配置：');
  console.error('');
  console.error('方式 1 - 编辑配置文件：');
  console.error('  编辑文件：/Users/macbook/.openclaw/workspace/.qwen-env');
  console.error('  将 YOUR_API_KEY_HERE 替换为你的真实 API Key');
  console.error('');
  console.error('方式 2 - 设置环境变量：');
  console.error('  export DASHSCOPE_API_KEY="your_api_key"');
  console.error('');
  console.error('获取 API Key: https://bailian.console.aliyun.com/');
  process.exit(1);
}

// 获取用户输入
const userMessage = process.argv.slice(2).join(' ');

if (!userMessage) {
  console.error('❌ 错误：请提供要问的问题');
  console.error('');
  console.error('使用示例：');
  console.error('  ./qwen-cli.js "你好，请介绍一下你自己"');
  console.error('  ./qwen-cli.js "今天天气怎么样"');
  console.error('  ./qwen-cli.js "写一首关于春天的诗"');
  process.exit(1);
}

console.log('🔄 正在向通义千问提问...');
console.log('');

const requestBody = JSON.stringify({
  model: 'qwen-plus',
  input: {
    messages: [
      { role: 'user', content: userMessage }
    ]
  },
  parameters: {
    result_format: 'message'
  }
});

const options = {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
};

const req = https.request(API_URL, options, (res) => {
  let data = '';
  
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    try {
      const result = JSON.parse(data);
      
      // 成功响应
      if (result.output && result.output.choices && result.output.choices[0]) {
        const message = result.output.choices[0].message;
        console.log('🤖 通义千问回复：');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log(message.content);
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('');
        console.log('✅ 请求成功！');
      } 
      // API 错误
      else if (result.code || result.message) {
        console.error('❌ API 错误：' + (result.message || result.code));
        console.error('');
        
        if (result.code === 'InvalidApiKey') {
          console.error('💡 可能原因：');
          console.error('  1. API Key 不正确或已过期');
          console.error('  2. 需要在阿里百炼控制台开通通义千问服务');
          console.error('  3. Key 可能属于其他服务');
          console.error('');
          console.error('📌 请检查：');
          console.error('  1. 访问 https://bailian.console.aliyun.com/');
          console.error('  2. 确认 API Key 正确');
          console.error('  3. 确保已开通「通义千问」服务');
        }
      } 
      // 未知响应
      else {
        console.error('❌ 未知响应格式：', data);
      }
    } catch (e) {
      console.error('❌ 解析响应失败：', e.message);
      console.error('原始响应：', data);
    }
  });
});

req.on('error', (e) => {
  console.error('❌ 请求失败：', e.message);
  process.exit(1);
});

req.write(requestBody);
req.end();
