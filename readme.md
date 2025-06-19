# AI 智能选车助手

这是一个基于人工智能的智能选车助手，旨在根据用户的购车需求提供合适的汽车推荐。用户可以通过自然语言输入需求，例如预算、用途、动力类型等，系统将结合汽车数据库，给出符合需求的车型推荐。

## 功能

- 根据用户的购车需求推荐合适的车型。
- 支持设置自定义的评分权重，以优化推荐。
- 提供车的详细信息，包括价格、用途、类型、动力、驱动方式、续航等。
- 用户可以下载推荐的车型数据为 CSV 文件。

## 系统要求

该项目使用了 Python 和 Streamlit，依赖以下的第三方库。

## 使用

## 克隆项目或下载代码。
   
   bash
   git clone https://github.com/your-repository.git
   cd your-repository

## 安装所需依赖。

pip install -r requirements.txt
## 设置 API 密钥。

如果需要自定义 API 密钥，可以在应用运行时输入。

## 启动 Streamlit 应用。
 streamlit run your_script.py
## 在浏览器中访问 http://localhost:8501，使用智能选车助手。