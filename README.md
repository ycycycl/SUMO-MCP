# SUMO-MCP: Leveraging the Model Context Protocol for Autonomous Traffic Simulation and Optimization


SUMO-MCP 解决了传统交通仿真工具（如SUMO）复杂手动工作流程的挑战。通过将大语言模型（LLM）代理与模型上下文协议（MCP）相结合，SUMO-MCP能够将高层次的自然语言用户请求自动转换为可执行的SUMO工作流程。

<p align="center">
  <a href="https://arxiv.org/abs/2506.03548">
    <img src="https://img.shields.io/badge/Paper-arXiv-b5212f.svg?logo=arxiv" />
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/LICENSE-MIT-green.svg" />
  </a>
</p>

## 📖 项目简介

随着大语言模型（LLM）的兴起，智能交通系统迎来了重大变革。这些先进的模型能够理解自然语言指令、分析数据并执行复杂任务。当配备外部工具调用能力时，LLM可以作为智能代理——一个能够理解用户请求并自动执行复杂任务的智能程序。

微观交通仿真软件SUMO（Simulation of Urban Mobility）是评估交通场景和优化信号配时的关键工具。然而，尽管SUMO应用广泛，但由于其复杂的接口（特别是TraCI）和较高的专业性要求，非专家用户使用起来仍然困难重重。

现有的LLM与SUMO集成研究虽然简化了用户交互，但仍需要用户遵循固定的预定义步骤，难以灵活应对新任务或意外需求。此外，这些系统依赖定制接口，难以集成额外工具或处理灵活的仿真工作流。

**SUMO-MCP正是为了解决这些问题而设计的提示辅助平台，让SUMO真正做到"即聊即用"。**

### 🌟 核心创新

1. **首次集成MCP与SUMO**：创建兼容MCP的SUMO工具套件，使代理能够动态发现和调用SUMO工具
2. **提示辅助仿真生成与评估**：用户可以轻松设置、运行和比较多种交通信号策略
3. **智能信号控制优化**：自动检测交通拥堵并基于仿真结果优化信号方案

### 💡 使用示例

传统工作流需要工程师手动配置仿真并反复分析结果，而SUMO-MCP让这一切变得简单：

```
用户输入：仿真海淀区晚高峰，对比Webster和绿波控制策略
系统响应：自动选择工具→组织工作流→处理交通优化→生成对比报告
```

通过模型上下文协议的客户端-服务器架构，SUMO-MCP提供动态发现、按需加载和结构化错误处理，**将数小时的脚本编写工作转变为几秒钟的自然语言提示**。

## 📦 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/ycycycl/SUMO-MCP.git
cd SUMO-MCP

# 安装 Python 依赖
pip install fastmcp qwen-agent flask flask-cors flask-socketio requests python-dotenv


```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# QWEN API 密钥（必需）
# 从 https://dashscope.console.aliyun.com/ 获取
QWEN_API_KEY=your_actual_qwen_api_key_here

# SUMO 安装路径（可选）
SUMO_HOME=/path/to/your/sumo/installation
```

### 3. 启动 MCP 服务器

```bash
# 启动主 SUMO-MCP 服务（端口 8014）
python mcp_sumo/sumo_tools.py

# 可选：启动专门的预定义工作流服务器
python mcp_sumo/sumo_simulation.py    # 仿真生成与评价（端口 8015）
python mcp_sumo/signal_optimization.py # 信号配时优化（端口 8016）
```

### 4. 客户端接入

#### 选项 1：接入现有 MCP 客户端
配置 Cursor、Claude Desktop 等支持 MCP 的客户端连接到服务器。

#### 选项 2：使用提供的演示客户端
```bash
# 启动后端服务
python demo/backend/app.py

# 启动前端界面
cd demo/frontend
python -m http.server 8000

# 在浏览器中访问 http://localhost:8000
```

## 📑 引用 / Citation

如果您认为 SUMO-MCP 对您的研究有帮助，请引用我们的论文：  

```bibtex
@inproceedings{ye2025sumo,
  title={SUMO-MCP: Leveraging the Model Context Protocol for Autonomous Traffic Simulation and Optimization},
  author={Ye, Chenglong and Xiong, Gang and Shang, Junyou and Dai, Xingyuan and Gong, Xiaoyan and Lv, Yisheng},
  booktitle={2025 China Automation Congress (CAC)},
  year={2025},
  organization={IEEE}
}
```