import os, json, pandas as pd
from openai import OpenAI

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


def score_car(car: dict, spec: dict, w: dict) -> float:
    score = 0.0

    # 一票否决：价格超过预算区间
    try:
        lo, hi = car["价格区间"].replace("万人民币", "").split("-")
        car_price = (int(lo) + int(hi)) * 10000 // 2
        budget_min = spec["预算区间"]["min"]
        budget_max = spec["预算区间"]["max"]
        if car_price < budget_min or car_price > budget_max:
            return 0  # 价格超出范围，直接返回 0 分
    except:
        pass

    # 一票否决：座位数少于要求
    if car["座位数"] < spec["座位数"]:
        return 0  # 座位数不满足要求，直接返回 0 分

    # 用途、车辆类型
    score += w["用途"] if car["用途"] == spec["用途"] else 0
    score += w["车辆类型"] if car["车辆类型"] == spec["车辆类型"] else 0

    # 预算评分（线性）
    try:
        lo, hi = car["价格区间"].replace("万人民币", "").split("-")
        car_price = (int(lo) + int(hi)) * 10000 // 2
        budget_min = spec["预算区间"]["min"]
        budget_max = spec["预算区间"]["max"]
        if budget_min <= car_price <= budget_max:
            score += w["预算区间"]
        else:
            score += range_score(car_price, (budget_min + budget_max) / 2, 100000, w["预算区间"])
    except:
        pass

    # 座位数
    if car["座位数"] >= spec["座位数"]:
        score += w["座位数"]

    # 动力 & 驱动
    # 如果用户明确指定了单一动力类型，给与更高的得分
    if spec["动力类型"] and car["动力类型"] == spec["动力类型"]:
        score += w["动力类型"] * 2  # 给定一个更高的权重
    else:
        score += w["动力类型"] if car["动力类型"] == spec["动力类型"] else 0

    score += w["驱动方式"] if car["驱动方式"] == spec["驱动方式"] else 0

    # 续航 / 油耗
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


def range_score(value, target, tolerance, weight):
    """改进的评分函数：当差值较小时，评分高；差值较大时，评分低"""
    delta = abs(value - target)
    if delta <= tolerance:
        return weight * (1 - delta / tolerance)  # 差值越小，得分越高
    return 0  # 如果差值超出容忍范围，返回0



def recommend_car(user_query: str, top_n: int = 3, custom_weights: dict = None):
    ai_resp = query_kimi(user_query)
    spec = ai_resp["需求"]
    weights = custom_weights or ai_resp["权重"]

    # 读取车型数据
    df = pd.read_json(VEHICLE_DB, orient="records")
    df["score"] = df.apply(lambda row: score_car(row, spec, weights), axis=1)

    # 过滤价格超出预算或座位数不足的车型
    df = df[(df["价格区间"].apply(lambda x: is_within_budget(x, spec["预算区间"]))) &
            (df["座位数"] >= spec["座位数"])]

    # 加微扰避免同分偏向001
    import numpy as np
    df["score"] += np.random.uniform(0, 0.01, size=len(df))

    top = df.sort_values(["score", "价格区间"], ascending=[False, True]).head(top_n)
    return top[["id", "名称", "价格区间", "用途", "车辆类型",
                "动力类型", "驱动方式", "座位数",
                "续航/续驶里程", "油耗/电耗", "score"]]

def is_within_budget(price_range, budget_range):
    try:
        lo, hi = price_range.replace("万人民币", "").split("-")
        car_price = (int(lo) + int(hi)) * 10000 // 2
        return budget_range["min"] <= car_price <= budget_range["max"]
    except:
        return False
