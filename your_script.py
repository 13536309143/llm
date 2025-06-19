# your_script.py (Streamlit前端)
import os
import streamlit as st
import pandas as pd
from ai_car_selector_kimi import recommend_car

st.set_page_config(page_title="🚘 AI 智能选车助手", layout="centered")
st.title("🚗 AI 智能选车助手")

st.markdown("**请输入你的购车需求**（如：我想买一辆适合家庭出行的中型SUV，预算20万以内，最好油电混合，续航超过800公里）：")
user_query = st.text_area("购车需求", height=120)

top_n = st.slider("展示前 N 个推荐结果", 1, 10, value=3)

with st.expander("⚖️ 高级设置：自定义评分权重（可选）"):
    weight_inputs = {
        "用途": st.slider("用途 权重", 0, 5, 3),
        "车辆类型": st.slider("车辆类型 权重", 0, 5, 2),
        "预算区间": st.slider("预算区间 权重", 0, 5, 4),
        "座位数": st.slider("座位数 权重", 0, 5, 1),
        "动力类型": st.slider("动力类型 权重", 0, 5, 2),
        "驱动方式": st.slider("驱动方式 权重", 0, 5, 1),
        "续航需求_km": st.slider("续航需求_km 权重", 0, 5, 3),
        "油耗上限_L_100km": st.slider("油耗上限_L_100km 权重", 0, 5, 3),
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
            result_df = recommend_car(user_query, top_n=top_n, custom_weights=weight_inputs)
        except Exception as e:
            st.error(f"调用失败：{e}")
            st.stop()

    if result_df.empty:
        st.warning("未找到符合条件的车型，请调整条件重试。")
    else:
        st.success("✅ 推荐完成！以下是匹配度最高的车型：")
        st.dataframe(
            result_df.rename(columns={
                "id": "车型ID",
                "名称": "名称",
                "价格区间": "价格",
                "用途": "用途",
                "车辆类型": "类型",
                "动力类型": "动力",
                "驱动方式": "驱动",
                "座位数": "座位",
                "续航/续驶里程": "续航/里程",
                "油耗/电耗": "油耗/电耗",
                "score": "得分"
            }),
            use_container_width=True,
            hide_index=True
        )

        # 下载按钮
        st.download_button(
            "📥 下载 CSV",
            data=result_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="car_recommendations.csv",
            mime="text/csv"
        )
