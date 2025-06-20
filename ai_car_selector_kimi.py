import os, json, pandas as pd
from openai import OpenAI
import numpy as np

# ---------- 基础配置 ----------
MOONSHOT_API_KEY = "sk-1n7PUR9ySyp4GSl9SQqX7sMFJwuwpIayyfyoPdwHQtrttV6h"
client = OpenAI(api_key=MOONSHOT_API_KEY,
                base_url="https://api.moonshot.cn/v1")

MODEL_NAME = "moonshot-v1-8k"
VEHICLE_DB = "vehicle_db_300_with_names_and_descriptions.json"  # 80 款车型 JSON 文件

SYSTEM_PROMPT = """
你是资深汽车顾问，请根据用户的自然语言需求，只输出符合以下 Schema 的 JSON，且必须严格遵循以下规则：
1. 如果车型的价格超出用户预算区间，直接排除该车型。
2. 如果车型的座位数少于用户要求的座位数，直接排除该车型。
3. 车辆的其他参数（例如动力类型、续航、油耗等）应根据用户需求进行匹配和优先推荐。
输出的JSON格式为：

{
  "需求": {
    "用途": "家庭出行",
    "车辆类型": "中型SUV",
    "预算区间": { "min": 150000, "max": 220000 },
    "座位数": 5,
    "动力类型": "油电混合",
    "驱动方式": "两驱",
    "续航需求_km": 800,
    "油耗上限_L_100km": 7.0
  },
  "权重": {
    "用途": 3,
    "车辆类型": 2,
    "预算区间": 4,
    "座位数": 1,
    "动力类型": 2,
    "驱动方式": 1,
    "续航需求_km": 3,
    "油耗上限_L_100km": 3
  }
}
"""

def query_kimi(user_text: str) -> dict:
    """
    获取AI返回的建议，包括需求和权重
    """
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        temperature=0.3,
    )
    content = completion.choices[0].message.content
    return json.loads(content)

def normalize_weights(weights):
    """
    权重归一化，使得总和为1
    """
    total_weight = sum(weights.values())
    if total_weight > 0:
        return {key: value / total_weight for key, value in weights.items()}
    return weights

def score_car(car: dict, spec: dict, w: dict) -> float:
    """
    计算每辆车的得分
    """
    score = 0.0

    # 权重归一化处理
    w = normalize_weights(w)

    # 价格评分
    try:
        lo, hi = car["价格区间"].replace("万人民币", "").split("-")
        car_price = (int(lo) + int(hi)) * 10000 // 2
        budget_min = spec["预算区间"]["min"]
        budget_max = spec["预算区间"]["max"]

        # 根据价格接近度评分，而不仅仅是是否在预算范围内
        if budget_min <= car_price <= budget_max:
            score += w["预算区间"]
        else:
            score += range_score(car_price, (budget_min + budget_max) / 2, 100000, w["预算区间"])
    except:
        pass

    # 座位数评分
    seat_diff = abs(car["座位数"] - spec["座位数"])
    if seat_diff == 0:
        score += w["座位数"]  # 精确匹配时满分
    elif seat_diff == 1:
        score += w["座位数"] * 0.75  # 如果差一座位，给75%的得分
    elif seat_diff == 2:
        score += w["座位数"] * 0.5  # 如果差两座位，给50%的得分
    else:
        score -= 0.1  # 如果差距很大，稍微惩罚

    # 用途、车辆类型的匹配
    if car["用途"] == spec["用途"]:
        score += w["用途"]
    else:
        score -= 0.1  # 轻微不匹配的惩罚

    if car["车辆类型"] == spec["车辆类型"]:
        score += w["车辆类型"]
    else:
        score -= 0.1  # 轻微不匹配的惩罚

    # 动力类型的匹配
    if spec["动力类型"] and car["动力类型"] == spec["动力类型"]:
        score += w["动力类型"] * 2  # 完全匹配得更高分
    elif spec["动力类型"] == "油电混合" and car["动力类型"] == "插电混动":
        score += w["动力类型"] * 1.5  # 油电混合与插电混动相似度高，给部分加分
    elif spec["动力类型"] == "插电混动" and car["动力类型"] == "油电混合":
        score += w["动力类型"] * 1.5

    # 续航 / 油耗评分
    try:
        if car["动力类型"] in ["纯电", "插电混动"]:
            rng = int(car["续航/续驶里程"].split()[0])
            score += range_score(rng, spec.get("续航需求_km", 0), 200, w["续航需求_km"])
        else:
            cons = float(car["油耗/电耗"].split()[0])
            score += range_score(spec.get("油耗上限_L_100km", 99), cons, 2, w["油耗上限_L_100km"])
    except:
        pass

    return round(score, 2)

def range_score(value, target, tolerance, weight, adjust_tolerance_factor=1.0):
    """
    根据车型的差异动态调整误差容忍度
    """
    tolerance *= adjust_tolerance_factor  # 动态调整容忍度
    delta = abs(value - target)
    if delta <= tolerance:
        return weight * (1 - delta / tolerance)  # 差值越小，得分越高
    return 0  # 如果差值超出容忍范围，返回0

def recommend_car(user_query: str, top_n: int = 3, custom_weights: dict = None):
    """
    获取推荐的车型
    """
    ai_resp = query_kimi(user_query)
    spec = ai_resp["需求"]
    weights = custom_weights or ai_resp["权重"]

    # 读取车型数据
    df = pd.read_json(VEHICLE_DB, orient="records")
    df["score"] = df.apply(lambda row: score_car(row, spec, weights), axis=1)

    # 排序时，综合考虑评分和价格
    top = df.sort_values(["score", "价格区间"], ascending=[False, True]).head(top_n)
    return top[["id", "名称", "价格区间", "用途", "车辆类型",
                "动力类型", "驱动方式", "座位数",
                "续航/续驶里程", "油耗/电耗", "score"]]
