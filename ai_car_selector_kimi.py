import os
import json
import pandas as pd
from openai import OpenAI
import numpy as np

MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-********************************************")
client = OpenAI(api_key=MOONSHOT_API_KEY, base_url="https://api.moonshot.cn/v1")
MODEL_NAME = "moonshot-v1-8k"
VEHICLE_DB = "vehicle_db_1000_named.json"
SYSTEM_PROMPT = """
你是一名资深汽车顾问，根据用户的自然语言购车需求，严格生成符合以下格式和要求的 JSON 数据。

【必填字段】以下字段必须提供，若用户未明确指出，请使用指定默认值：
- 用途（可选项：家庭出行、城市代步、商务接待、长途出行、运动旅行、越野探险；默认："家庭出行"）
- 车辆类型（可选项：中型SUV、小型掀背、大型轿车、旅行车、房车、小型两厢、Coupe、MPV、硬派SUV、皮卡；默认："中型SUV"）
- 预算区间（格式：{"min": 数字, "max": 数字}，默认：{"min": 0, "max": 200000}）
- 座位数（整数，默认：5）
- 动力类型（可选项：油电混合、纯电、3.0T汽油、1.6L汽油、插电混动、2.5L汽油、氢燃料电池；默认："油电混合"）
- 驱动方式（可选项：两驱、前驱、后驱、四驱；默认："两驱"）
- 续航需求_km（单位：公里，默认：800）
- 能耗上限（数字，单位根据动力类型自动判定：燃油车为 L/100km，电动车为 kWh/100km；默认：7.0）

【说明】
- 无需让用户输入单位，系统将自动判断。
- “能耗上限”代表用户希望的最大单位能耗，不论是油耗还是电耗。

【硬性筛选规则】
1. 车辆价格超出预算直接排除。
2. 车辆座位数不足直接排除。

【输出格式】
仅输出以下 JSON 格式，不要添加任何多余内容：

{
  "需求": {
    "用途": "...",
    "车辆类型": "...",
    "预算区间": { "min": ..., "max": ... },
    "座位数": ...,
    "动力类型": "...",
    "驱动方式": "...",
    "续航需求_km": ...,
    "能耗上限": ...
  },
  "权重": {
    "用途": 数字,
    "车辆类型": 数字,
    "预算区间": 数字,
    "座位数": 数字,
    "动力类型": 数字,
    "驱动方式": 数字,
    "续航需求_km": 数字,
    "能耗上限": 数字
  }
}

请严格遵守字段名、格式和选项要求，确保字段齐全，不可遗漏。
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
    return json.loads(completion.choices[0].message.content)

def normalize_weights(weights):
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()} if total else weights

def range_score(value, target, tolerance, weight):
    delta = abs(value - target)
    return weight * (1 - delta / tolerance) if delta <= tolerance else 0

def score_car(car, spec, w):
    score = 0.0
    w = normalize_weights(w)

    try:
        lo, hi = car["价格区间"].replace("万人民币", "").split("-")
        car_price = (int(lo) + int(hi)) * 5000
        bmin, bmax = spec["预算区间"]["min"], spec["预算区间"]["max"]
        if bmin <= car_price <= bmax:
            score += w["预算区间"]
        else:
            score += range_score(car_price, (bmin + bmax) / 2, 100000, w["预算区间"])
    except: pass

    seat_diff = abs(car["座位数"] - spec["座位数"])
    score += w["座位数"] * {0:1.0,1:0.75,2:0.5}.get(seat_diff, -0.1)

    if car["用途"] == spec["用途"]: score += w["用途"]
    if car["车辆类型"] == spec["车辆类型"]: score += w["车辆类型"]
    if car["驱动方式"] == spec["驱动方式"]: score += w["驱动方式"]

    if car["动力类型"] == spec["动力类型"]:
        score += w["动力类型"] * 2
    elif (car["动力类型"], spec["动力类型"]) in [("油电混合", "插电混动"), ("插电混动", "油电混合")]:
        score += w["动力类型"] * 1.5

    try:
        energy_value = float(car["油耗/电耗"].split()[0])
        if car["动力类型"] in ["纯电", "氢燃料电池"]:
            score += range_score(energy_value, spec["能耗上限"], 5, w["能耗上限"])
            score += range_score(int(car["续航/续驶里程"].split()[0]), spec["续航需求_km"], 200, w["续航需求_km"])
        else:
            score += range_score(energy_value, spec["能耗上限"], 2, w["能耗上限"])
    except: pass

    return round(score, 2)

def recommend_car(user_query: str, top_n: int = 3, custom_weights: dict = None, custom_spec: dict = None):
    if custom_spec is None:
        ai_resp = query_kimi(user_query)
        spec = ai_resp["需求"]
    else:
        spec = custom_spec

    weights = custom_weights or query_kimi(user_query)["权重"]

    df = pd.read_json(VEHICLE_DB, orient="records")
    df["score"] = df.apply(lambda row: score_car(row, spec, weights), axis=1)
    return df.sort_values(["score", "价格区间"], ascending=[False, True]).head(top_n)[
        ["id", "名称", "价格区间", "用途", "车辆类型", "动力类型", "驱动方式", "座位数", "续航/续驶里程", "油耗/电耗", "score"]
    ]
