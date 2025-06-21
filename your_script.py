import os
import streamlit as st
import pandas as pd
from ai_car_selector_kimi import recommend_car, query_kimi

st.set_page_config(page_title="🚘 AI 智能选车助手", layout="centered")
st.title("🚗 AI 智能选车助手")

st.markdown("**请输入你的购车需求**（如：我想买一辆适合家庭出行的中型SUV，预算20万以内，最好油电混合，续航超过800公里）：")
user_query = st.text_area("购车需求", height=120)
top_n = st.slider("展示前 N 个推荐结果", 1, 10, value=3)

# 自动判断单位（非常简化逻辑）
default_unit = "L/100km"
if any(x in user_query for x in ["纯电", "电动", "电车", "氢", "氢燃料"]):
    default_unit = "kWh/100km"

with st.expander("⚖️ 高级设置：自定义评分权重（可选）"):
    weight_inputs = {
        "用途": st.slider("用途 权重", 0, 5, 1),
        "车辆类型": st.slider("车辆类型 权重", 0, 5, 1),
        "预算区间": st.slider("预算区间 权重", 0, 5, 1),
        "座位数": st.slider("座位数 权重", 0, 5, 1),
        "动力类型": st.slider("动力类型 权重", 0, 5, 1),
        "驱动方式": st.slider("驱动方式 权重", 0, 5, 1),
        "续航需求_km": st.slider("续航需求_km 权重", 0, 5, 1),
        "能耗上限": st.slider(f"能耗上限（单位：{default_unit}） 权重", 0, 5, 1),
    }


with st.expander("🔐 API Key 设置（当前会话内有效）"):
    custom_key = st.text_input("Moonshot API Key", type="password")
    if custom_key:
        os.environ["MOONSHOT_API_KEY"] = custom_key

if st.button("开始智能选车 🚀"):
    if not user_query.strip():
        st.error("请输入购车需求")
        st.stop()

    with st.spinner("正在匹配推荐车型…"):
        try:
            ai_resp = query_kimi(user_query)
            spec = ai_resp["需求"]

            if any(val > 0 for val in weight_inputs.values()):
                weights = weight_inputs
                st.info("✅ 使用手动设置的评分权重")
            else:
                weights = ai_resp["权重"]
                st.info("⚠️ 使用 AI 自动推荐权重")

            st.subheader("AI 分析出的购车需求：")
            st.json(spec)
            st.write("**使用的评分权重：**")
            st.json(weights)

            result_df = recommend_car(
                user_query=user_query,
                top_n=top_n,
                custom_weights=weights,
                custom_spec=spec
            )
        except Exception as e:
            st.error(f"调用失败：{e}")
            st.stop()

    if result_df.empty:
        st.warning("未找到符合条件的车型，请调整条件重试。")
    else:
        st.success("✅ 推荐完成，以下是匹配度最高的车型：")
        st.dataframe(result_df.rename(columns={
            "id": "车型ID",
            "名称": "名称",
            "价格区间": "价格",
            "用途": "用途",
            "车辆类型": "类型",
            "动力类型": "动力",
            "驱动方式": "驱动",
            "座位数": "座位",
            "续航/续驶里程": "续航",
            "油耗/电耗": "油耗",
            "score": "得分"
        }), use_container_width=True)

        st.download_button(
            "📥 下载推荐结果 CSV",
            data=result_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="car_recommendations.csv",
            mime="text/csv"
        )
