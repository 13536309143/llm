# AI 智能选车系统 - 功能与实现逻辑报告

## 一、`ai_car_selector_kimi.py` 功能逻辑详解

### 🎯 核心功能
实现汽车推荐系统的“**智能意图分析 + 多维精确评分**”模块，结合语言模型对用户意图进行结构化解析，并对候选车辆打分排序推荐。

### 📦 模块职责

| 函数名 | 功能说明 |
|--------|----------|
| `query_kimi()` | 调用大语言模型（Moonshot）分析用户自然语言需求，返回结构化 JSON（需求 + 权重） |
| `score_car()` | 根据结构化需求，对每辆车进行匹配打分 |
| `recommend_car()` | 加载车辆数据库，应用评分函数并返回 Top N 推荐 |

### 📐 评分逻辑说明（`score_car`）

- **硬性过滤**：预算区间不符、座位数不足将直接排除；
- **完全匹配项得满分**：用途、车辆类型、驱动方式等；
- **动力类型匹配加权**：完全匹配加 2 倍权重，插混与油混视为兼容得 1.5 倍；
- **模糊评分项使用 `range_score`**：
  - 价格 ±10 万容差
  - 续航 ±200km
  - 能耗单位自动判断：
    - 电车为 `kWh/100km`（容差 5）
    - 油车为 `L/100km`（容差 2）

### 🧠 智能意图分析（`query_kimi`）

- 使用 Moonshot 大模型生成标准 JSON，包括：
  - `需求`：结构化字段，如 `"动力类型": "油电混合"` 等；
  - `权重`：表示用户偏好的重要程度；
- `SYSTEM_PROMPT` 明确引导生成格式、字段名、默认值；
- 支持字段智能补全与默认值填充。

---

## 二、`your_script.py` 功能逻辑详解

### 🎯 核心功能
基于 Streamlit 构建用户界面，支持自然语言输入购车需求并查看推荐结果，支持权重配置与 CSV 导出。

### 🧩 界面结构与功能区

| 区域 | 功能说明 |
|------|----------|
| 顶部输入框 | 输入自然语言购车需求 |
| Top-N 滑块 | 控制展示前 N 个推荐结果 |
| 高级设置 | 提供 8 个维度评分权重滑动条 |
| API Key 区 | 允许设置 Moonshot API Key |
| 推荐结果区 | 显示推荐车型表格并支持 CSV 下载 |

### 🧠 智能行为与交互逻辑

#### 权重模式自动切换
- 若设置权重滑动条 → 使用手动权重；
- 否则 → 使用 LLM 推荐默认权重。

#### 能耗单位自动提示
- 根据关键词如“电”、“氢”判断动力类型；
- 滑块提示单位动态设置为 `kWh/100km` 或 `L/100km`。

---

## 三、模块间协作流程

```text
[用户输入自然语言需求]
           ↓
   [your_script.py] 接收输入
           ↓
[query_kimi] 使用大语言模型转为结构化 JSON
           ↓
[recommend_car] 载入车辆数据库，打分排序
           ↓
[score_car] 根据规则对每辆车计算匹配得分
           ↓
       [展示推荐结果]
```

---

## ✅ 系统特点总结

- ✅ 自然语言输入，零学习成本；
- ✅ 多维度评分机制，支持权重控制；
- ✅ 电车 / 油车 能耗单位自动判断；
- ✅ 推荐结果可视化 + 可导出；
- ✅ 模块清晰，便于后续集成与扩展。
