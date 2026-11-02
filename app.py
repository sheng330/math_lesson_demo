import streamlit as st
import base64, json, requests, ast, time, os
from collections import Counter

# ==================== 智谱 API Key（用 Secrets，不要把 Key 写进代码） ====================
# 本机运行：在 .streamlit/secrets.toml 里写 ZHIPU_API_KEY = "你的Key"
# 云端运行：在 Streamlit Cloud 的 Secrets 里填 ZHIPU_API_KEY
API_KEY = st.secrets["ZHIPU_API_KEY"]
# ====================================================================

# ==================== 免费模型配置（2026-11 智谱免费档） ====================
# 视觉识别（只读图抽文字）：glm-4.6v-flash（免费）
# 判卷 + 讲评（数学推理）：glm-4.7-flash（免费文本模型，推理远强于视觉 flash）
# 视觉识别模型链：优先用第一个，限流时自动切换下一个免费模型
视觉模型链 = ["glm-4.6v-flash", "glm-4.1v-thinking-flash"]
# 文本推理模型链：判卷/讲评用（全部免费）
文本模型链 = ["glm-4.7-flash", "glm-4.5-flash", "glm-4-flash-250414"]
TEMPERATURE  = 0.0   # 判卷/讲评用低温度，减少随机性
# 提示：免费模型有并发/频率限制（429 错误码 1302 账户限流 / 1305 平台过载）。
# 已做三件事缓解：① 限流时按错误码自适应退避重试；② 单个模型持续限流自动换免费备胎模型；
# ③ 任务运行期间禁止重复点击按钮（防止并发堆积）。
# ====================================================================

st.set_page_config(page_title="数学试卷讲评 Demo", layout="wide")
st.title("数学试卷 AI 讲评 Demo")

# ========== 内置卷子库 ==========
内置卷子库 = {
    "样卷 1（AI生成）": "builtin_papers/paper_1.jpg",
    "样卷 2（手写卷转录为打字版）": "builtin_papers/paper_2.jpg",
    "样卷 3（手写卷）": "builtin_papers/paper_3.jpg"
}

# ========== 常量 ==========
教材选项 = ["高一 · 必修第一册（沪教版）"]

知识点体系库 = {
    "高一 · 必修第一册（沪教版）": """
集合与逻辑 > 集合的概念与表示 > 元素与集合的关系（∈、∉）
集合与逻辑 > 集合的概念与表示 > 集合的表示方法（列举法、描述法、区间）
集合与逻辑 > 集合间的关系 > 子集与真子集
集合与逻辑 > 集合的运算 > 交集
集合与逻辑 > 集合的运算 > 并集
集合与逻辑 > 集合的运算 > 补集
集合与逻辑 > 命题与逻辑 > 充分条件与必要条件
集合与逻辑 > 命题与逻辑 > 充要条件
集合与逻辑 > 证明方法 > 反证法

等式与不等式 > 等式的性质 > 等式的传递性、加法性质、乘法性质
等式与不等式 > 方程的解集 > 一元一次方程的解集（含参讨论）
等式与不等式 > 方程的解集 > 一元二次方程的解集（判别式）
等式与不等式 > 方程的解集 > 一元二次方程根与系数的关系（韦达定理）
等式与不等式 > 不等式的性质 > 作差比较法
等式与不等式 > 不等式的性质 > 不等式的基本性质（传递性、加法、乘法）
等式与不等式 > 不等式的求解 > 一元一次不等式及不等式组
等式与不等式 > 不等式的求解 > 一元二次不等式（与判别式、二次函数图像结合）
等式与不等式 > 不等式的求解 > 分式不等式
等式与不等式 > 不等式的求解 > 含绝对值不等式
等式与不等式 > 基本不等式 > 平均值不等式（(a+b)/2 ≥ √ab）及其应用
等式与不等式 > 基本不等式 > 三角不等式（|a+b| ≤ |a|+|b|）

幂、指数与对数 > 指数幂 > 整数指数幂
幂、指数与对数 > 指数幂 > 有理数指数幂与根式
幂、指数与对数 > 指数幂 > 实数指数幂的运算性质
幂、指数与对数 > 对数 > 对数的定义（log_a N）
幂、指数与对数 > 对数 > 对数的运算性质（积、商、幂）
幂、指数与对数 > 对数 > 换底公式

幂函数、指数函数与对数函数 > 幂函数 > 幂函数的定义域与图像
幂函数、指数函数与对数函数 > 幂函数 > 幂函数的单调性
幂函数、指数函数与对数函数 > 指数函数 > 指数函数的定义与图像
幂函数、指数函数与对数函数 > 指数函数 > 指数函数的单调性
幂函数、指数函数与对数函数 > 指数函数 > 指数函数的值域与定点
幂函数、指数函数与对数函数 > 对数函数 > 对数函数的定义与图像
幂函数、指数函数与对数函数 > 对数函数 > 对数函数的单调性
幂函数、指数函数与对数函数 > 对数函数 > 对数函数的定义域与定点
幂函数、指数函数与对数函数 > 对数函数 > 指数函数与对数函数互为反函数

函数的概念、性质及应用 > 函数的概念 > 函数的定义域求解
函数的概念、性质及应用 > 函数的概念 > 函数的值域求解
函数的概念、性质及应用 > 函数的表示 > 解析法、列表法、图像法
函数的概念、性质及应用 > 函数的表示 > 分段函数
函数的概念、性质及应用 > 函数的奇偶性 > 奇偶函数的判断与证明
函数的概念、性质及应用 > 函数的单调性 > 用定义证明单调性（作差法）
函数的概念、性质及应用 > 函数的单调性 > 含参函数的单调性讨论（用定义法）
函数的概念、性质及应用 > 函数的最值 > 利用单调性求最值
函数的概念、性质及应用 > 函数的最值 > 二次函数在给定区间上的最值
函数的概念、性质及应用 > 函数的应用 > 建立函数关系
函数的概念、性质及应用 > 函数的零点 > 函数零点的概念
函数的概念、性质及应用 > 函数的零点 > 二分法求近似零点
函数的概念、性质及应用 > 反函数（选学） > 反函数的概念与求法
""",
}

本册范围 = """
沪教版高一必修第一册包含：
第1章 集合与逻辑
第2章 等式与不等式
第3章 幂、指数与对数
第4章 幂函数、指数函数与对数函数
第5章 函数的概念、性质及应用
"""

超纲约束 = """
【超纲约束】
- 禁止使用导数、三角函数、数列、平面向量、立体几何、解析几何、概率统计。
- 判断单调性必须用定义法，不能用导数。
- 求最值只能用单调性、基本不等式或配方。
"""

参考标签 = ["审题偏差", "知识性错误", "策略性错误", "执行性错误", "过程不完整", "其他/混合型"]
标签说明 = {
    "审题偏差": "看错、漏看或误解题目条件",
    "知识性错误": "概念、公式、定理记错或用错",
    "策略性错误": "知道知识点，但选错方法或不知从何下手",
    "执行性错误": "方法对，但算错、变形错、符号错",
    "过程不完整": "方法对、算得也对，但漏了必要步骤",
    "其他/混合型": "无法归入以上任一项",
}
显示选项 = [f"{k}：{v}" for k, v in 标签说明.items()]
显示转短名 = {f"{k}：{v}": k for k, v in 标签说明.items()}
短名转显示 = {k: f"{k}：{v}" for k, v in 标签说明.items()}

标签使用规则 = """
1. 审题偏差：看错、漏看条件。
2. 知识性错误：公式、定理用错。
3. 策略性错误：选错方法。
4. 执行性错误：算错、符号错。
5. 过程不完整：漏了分类讨论、验证等。
6. 其他/混合型。
优先级：审题偏差 > 知识性错误 > 策略性错误 > 执行性错误 > 过程不完整。
"""

# 状态选项：新增“时间不够没来得及做”
状态选项 = ["请选择", "完全没思路", "时间不够没来得及做", "卡在某一步", "写完了但做错"]

for k in ["AI全部结果", "识别结果", "预判", "诊断结果", "最终归因", "原始文本"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ========== 工具函数 ==========
def 调用模型(prompt, key, model, img_b64=None, mime=None, temperature=TEMPERATURE, max_tokens=None, max_retries=3):
    """统一调用智谱 API。img_b64 传了就按多模态（图片+文本），否则纯文本。
    429 限流时不立即放弃：按错误码自适应退避（1302 账户限流等 10s 起，1305 平台过载等更久），
    重试次数有限，超限就交给上层换下一个免费模型，避免卡死等待。"""
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {key}"}
    if img_b64:
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            {"type": "text", "text": prompt},
        ]
    else:
        content = prompt  # 纯文本直接用字符串
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [{"role": "user", "content": content}],
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    最后的错误 = ""
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=180)
            if r.status_code == 200:
                raw = r.json()["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1] if "\n" in raw else raw
                    raw = raw.rsplit("```", 1)[0]
                return raw.strip()
            # 解析错误码（1302=账户速率限制，1305=平台服务过载）
            code, msg = None, r.text[:200]
            try:
                err = r.json().get("error", {})
                if isinstance(err, dict):
                    code = err.get("code")
                    msg = err.get("message", "") or ""
            except Exception:
                pass
            最后的错误 = f"HTTP {r.status_code} 错误码 {code}：{msg}"
            if r.status_code == 429:
                wait = 10 + attempt * 10          # 账户限流：10s 起逐步退避
                if code == 1305:
                    wait = 20 + attempt * 15      # 平台过载：等更久一点
                time.sleep(wait)
                continue
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            最后的错误 = str(e)
            if attempt == max_retries - 1:
                break
            time.sleep(5)
    raise Exception(f"「{model}」多次调用仍失败：{最后的错误}")

def 调用模型带回退(prompt, key, 模型链, img_b64=None, mime=None, temperature=TEMPERATURE, max_tokens=None, 校验=None):
    """依次尝试一组免费模型；调用异常、或返回内容通不过校验（如不是 JSON）时自动切换下一个模型。"""
    最后的错误 = ""
    最后的原始 = ""
    for model in 模型链:
        try:
            raw = 调用模型(prompt, key, model, img_b64=img_b64, mime=mime,
                            temperature=temperature, max_tokens=max_tokens)
            if 校验 is not None:
                ok, reason = 校验(raw)
                if not ok:
                    最后的错误 = f"「{model}」返回内容未通过校验（{reason}）"
                    最后的原始 = raw
                    continue
            return raw
        except Exception as e:
            最后的错误 = str(e)
    if 最后的原始:
        raise Exception(f"返回内容不是有效 JSON（多个模型均失败）。最后返回内容开头：{最后的原始[:200]}")
    raise Exception(f"多个免费模型调用均失败（可能当日额度用尽或平台过载，可稍后再试或到智谱控制台查看速率限制）：{最后的错误}")

def 解析(raw):
    """尽量把模型输出解析为 Python 对象：直接解析 → 从文本中截取最外层 JSON 片段再解析。"""
    if not isinstance(raw, str):
        return None, raw
    raw = raw.strip()
    for fn in (json.loads, ast.literal_eval):
        try:
            return fn(raw), None
        except Exception:
            pass
    # 模型偶尔会在 JSON 前后加说明文字：截取最外层 [ ] 或 { } 再试
    for a, b in (("[", "]"), ("{", "}")):
        i, j = raw.find(a), raw.rfind(b)
        if i != -1 and j > i:
            sub = raw[i:j + 1]
            for fn in (json.loads, ast.literal_eval):
                try:
                    return fn(sub), None
                except Exception:
                    pass
    return None, raw

def 解包列表(结果):
    """模型偶尔把数组包在对象里（如 {"结果": [...]}），取出第一个列表；没有则原样返回。"""
    if isinstance(结果, dict):
        for v in 结果.values():
            if isinstance(v, list):
                return v
    return 结果

def 校验识别(raw):
    """识别结果必须能解析为「非空、全为对象」的 JSON 数组，否则视为模型失败，交给下一个模型重试。"""
    结果, _ = 解析(raw)
    结果 = 解包列表(结果)
    if isinstance(结果, list) and len(结果) > 0 and all(isinstance(t, dict) for t in 结果):
        return True, ""
    return False, "不是有效 JSON 数组"

def 校验判卷(raw):
    """判卷结果必须能解析为「非空」的 JSON 数组，否则视为模型失败，交给下一个模型重试。"""
    结果, _ = 解析(raw)
    结果 = 解包列表(结果)
    if isinstance(结果, list) and len(结果) > 0:
        return True, ""
    return False, "不是有效 JSON 数组"

def 清理数学文本(s):
    if not isinstance(s, str): return s
    s = s.replace("\x0c", "\\f").replace("\\(", "$").replace("\\)", "$")
    return s.replace("\\[", "$$").replace("\\]", "$$")

def 规范化(结果):
    if not isinstance(结果, list): return 结果
    for 题 in 结果:
        题["题号"] = str(题.get("题号", "?"))
        if isinstance(题.get("参考标签"), str):
            题["参考标签"] = [题["参考标签"]]
        for 字段 in ["错误性质描述", "判断证据", "解答", "重点提示", "讲评", "可操作建议", "与学生预判的对照"]:
            v = 题.get(字段)
            if isinstance(v, list): v = "\n".join(str(x) for x in v)
            elif v is None: v = ""
            题[字段] = 清理数学文本(v)
    return 结果

def 刷新():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def 压缩图片(字节, 长边=1600, 质量=82):
    """把图片压到长边≤1600px 再传给视觉模型，识别速度大幅提升。
    没装 Pillow 或失败时原样返回。"""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(字节))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > 长边:
            r = 长边 / max(w, h)
            img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=质量)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return 字节, None

# ========== 侧边栏 ==========
教材 = st.sidebar.selectbox("选择教材范围", 教材选项)
知识点体系 = 知识点体系库[教材]

# ========== 图片来源：上传 or 内置 ==========
st.subheader("选择试卷")
st.caption("隐私提示：试卷图片会上传到智谱 AI 接口处理。请确保图片中不含姓名、学校、学号、班级等个人信息，如有请先打码或裁剪后再上传。")
图片来源 = st.radio("图片来源", ["上传图片", "使用内置卷子"], horizontal=True)

图片字节 = None
图片类型 = None

if 图片来源 == "上传图片":
    uploaded = st.file_uploader("上传试卷", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        uploaded.seek(0)
        图片字节 = uploaded.read()
        图片类型 = uploaded.type or "image/jpeg"
else:
    卷子名 = st.selectbox("选择内置卷子", list(内置卷子库.keys()))
    路径 = 内置卷子库[卷子名]
    if os.path.exists(路径):
        with open(路径, "rb") as f:
            图片字节 = f.read()
        图片类型 = "image/png" if 路径.lower().endswith(".png") else "image/jpeg"
    else:
        st.error(f"内置卷子文件不存在：{路径}。请确认 builtin_papers 文件夹和文件名。")

if 图片字节 is not None:
    st.image(图片字节, caption="当前试卷", use_column_width=True)
    st.caption("确认试卷无误后，点击下方按钮开始识别。")

# ========== 第1步：识别 + 判卷（两阶段，读图与推理分离） ==========
if st.button("① 开始识别"):
    if 图片字节 is None:
        st.warning("请先选择或上传试卷图片")
    elif st.session_state.get("正在处理"):
        st.warning("上一次任务还在处理中，请稍候再试。")
    else:
        st.session_state.正在处理 = True
        # 先压缩图片再传给视觉模型（提速）
        图片字节, 压缩mime = 压缩图片(图片字节)
        mime = 压缩mime or 图片类型
        img_b64 = base64.b64encode(图片字节).decode()

        # ---- 阶段一：视觉识别（免费视觉模型，只抽文字，不判对错） ----
        识别prompt = """
请仔细阅读这张高中数学试卷照片，逐题识别卷面上的题目，不要遗漏任何一道题。

对每一道题输出：
- 题号（按卷面顺序的编号，字符串）
- 题干（完整转写题目文字）
- 学生作答（该题下学生的书写内容，尽力转写；实在看不清写“（看不清）”）

要求：
- 打印题和手写作答都要识别，不要漏题。
- 只做文字转写，不要解题、不要判对错、不要讲评。
- 忽略试卷上的姓名、学校、学号、班级等与题目无关的个人信息，不要转写。
- 数学公式用线性文本表达，例如：f(x)=sqrt(x-1)+1/(x-2)、x^2-3x+2≤0、log2(x)≥1、|x-1|≤2、x^2+bx+c、a≠0、Δ=b^2-4ac。

输出 JSON 数组，每项只含 题号、题干、学生作答 三个字段。只输出 JSON，不要输出任何其他文字。
"""
        with st.spinner("识别中（免费模型较慢，约 2-4 分钟，请耐心等待）..."):
            try:
                raw = 调用模型带回退(识别prompt, API_KEY, 视觉模型链, img_b64=img_b64, mime=mime, max_tokens=3000, 校验=校验识别)
            except Exception as e:
                st.session_state.原始文本 = str(e)
                st.session_state.正在处理 = False
                st.warning(str(e) + "\n可点击上方『① 开始识别』按钮重试。")
                st.stop()
            识别结果, 原始 = 解析(raw)
            识别结果 = 解包列表(识别结果)
        if not 识别结果 or not isinstance(识别结果, list):
            st.session_state.原始文本 = 原始
            st.session_state.正在处理 = False
            st.warning("识别失败（返回内容不是有效 JSON）。可点击上方『① 开始识别』按钮重试。\n内容开头：\n" + str(原始)[:200])
            st.code(原始)
            st.stop()

        # ---- 阶段二：文本判卷（免费文本模型，独立解题后与学生作答比较） ----
        判卷prompt = f"""
你是高中数学阅卷老师。下面是刚从试卷照片中识别出来的题目和学生作答（识别可能有少量误差，以你能读到的内容为准）。

【题目列表】
{json.dumps(识别结果, ensure_ascii=False, indent=1)}

【超纲约束】{超纲约束}

请对每一道题：
1. 先自己完整解一遍，得到标准答案。特别注意含参问题、判别式（Δ）的三种情况、定义域限制、区间端点能否取到等容易遗漏的关键情况。
2. 再与学生作答逐项比较，判定“正确”或“错误”（学生没写的判“错误”，并在判定说明里注明“未作答”）。
3. 若判“错误”，用一句话写出“关键检查点”：指出学生解题中遗漏或出错的那个关键情况，用通用表述，不要只写具体数值。例如：
   · “遗漏了参数取某个特殊值的情况”
   · “遗漏了二次方程判别式为零或为负的情况”
   · “遗漏了定义域端点或分母为零的限制”
   · “遗漏了区间端点能否取到”
   · “某一步的符号或不等号方向处理错误”
   若只是计算错误，写“仅计算错误，无遗漏关键情况”；若判“正确”，写“无”。
4. 全部完成后整体复核一遍：重新检查每一道题的判定是否可靠，若发现草率判定或前后矛盾，以复核后的结果为准修正。

输出 JSON 数组，每项只含 题号、AI判定（“正确”/“错误”）、判定说明（一句话）、关键检查点 四个字段。
只输出 JSON，不要输出任何其他文字。
"""
        with st.spinner("识别中（免费模型较慢，约 2-4 分钟，请耐心等待）..."):
            try:
                raw2 = 调用模型带回退(判卷prompt, API_KEY, 文本模型链, max_tokens=4000, 校验=校验判卷)
            except Exception as e:
                st.session_state.原始文本 = str(e)
                st.session_state.正在处理 = False
                st.warning(str(e) + "\n可点击上方『① 开始识别』按钮重试。")
                st.stop()
            判卷列表, 原始2 = 解析(raw2)
            判卷列表 = 解包列表(判卷列表)
        if not 判卷列表 or not isinstance(判卷列表, list):
            st.session_state.原始文本 = 原始2
            st.session_state.正在处理 = False
            st.warning("判卷失败（返回内容不是有效 JSON）。可点击上方『① 开始识别』按钮重试。\n内容开头：\n" + str(原始2)[:200])
            st.code(原始2)
            st.stop()

        # 合并识别结果与判卷结果
        判卷映射 = {str(t.get("题号")): t for t in 判卷列表 if isinstance(t, dict)}
        全部结果 = []
        for 题 in 识别结果:
            j = 判卷映射.get(str(题.get("题号")), {})
            全部结果.append({
                "题号": str(题.get("题号", "?")),
                "题干": 题.get("题干", ""),
                "学生作答": 题.get("学生作答", ""),
                "AI判定": j.get("AI判定", "未知"),
                "判定说明": j.get("判定说明", ""),
                "关键检查点": j.get("关键检查点", "无"),
            })
        st.session_state.AI全部结果 = 规范化(全部结果)
        st.session_state.识别结果 = None
        st.session_state.预判 = None
        st.session_state.诊断结果 = None
        st.session_state.最终归因 = None
        st.session_state.正在处理 = False
        st.success(f"识别到 {len(全部结果)} 道题，AI 判卷完成。请在下方的【校对确认】环节核实错题。")

# ========== 第1.5步：人工校对确认 ==========
if st.session_state.get("AI全部结果"):
    st.subheader("①.5 校对确认（请核实 AI 的判卷结果）")
    st.caption("AI 视觉识别有限，偶尔会看错题号或漏判。请根据原图，勾选你认为**真正做错**的题目。")

    所有题目 = st.session_state.AI全部结果
    错题选项 = [f"第 {t.get('题号', '?')} 题" for t in 所有题目]
    AI判定的错题 = [f"第 {t.get('题号', '?')} 题" for t in 所有题目 if t.get("AI判定") in ["错误", "错"]]

    with st.expander("查看 AI 对所有题目的判定详情", expanded=False):
        for 题 in 所有题目:
            st.write(f"**第 {题.get('题号', '?')} 题**：AI 判定【{题.get('AI判定', '未知')}】—— {题.get('判定说明', '')}")
            if 题.get("关键检查点") and 题.get("关键检查点") != "无":
                st.caption(f"关键检查点：{题.get('关键检查点')}")

    确认的错题 = st.multiselect(
        "请勾选并确认本次需要讲评的错题（默认选中 AI 判错的题）：",
        错题选项,
        default=AI判定的错题
    )

    if st.button("确认错题，进入预判环节"):
        if not 确认的错题:
            st.warning("请至少选择一道错题")
        else:
            选中题号 = [x.replace("第 ", "").replace(" 题", "") for x in 确认的错题]
            最终错题列表 = [t for t in 所有题目 if t.get("题号") in 选中题号]
            st.session_state.识别结果 = 最终错题列表
            st.session_state.预判 = None
            st.session_state.诊断结果 = None
            st.session_state.最终归因 = None
            刷新()

# ========== 第2步：学生预判 ==========
if st.session_state.get("识别结果"):
    st.subheader("② 你的预判")
    st.caption("对每道错题，先选你的状态（必选）。选“卡在某一步”需描述卡点；选“写完了但做错”需选错误类型。")

    预判 = {}
    全部通过 = True

    for 题 in st.session_state.识别结果:
        题号 = 题.get("题号", "?")
        st.markdown(f"#### 第 {题号} 题")
        st.write(f"**题干**：{题.get('题干','')}")
        st.write(f"**你的作答**：{题.get('学生作答','')}")

        状态 = st.radio(f"第{题号}题你的情况（必选）", 状态选项, key=f"s{题号}")
        if 状态 == "请选择":
            全部通过 = False
            st.caption("⚠️ 请先选择你的情况")

        卡点描述 = ""
        if 状态 == "卡在某一步":
            卡点描述 = st.text_area(f"第{题号}题你卡在哪一步？（必填）", key=f"k{题号}", placeholder="例如：不知道怎么讨论参数 a 的符号")
            if not 卡点描述.strip():
                全部通过 = False
                st.caption("⚠️ 请描述你卡在哪一步")

        选中的显示 = st.multiselect(
            f"第{题号}题错误类型（仅“写完了但做错”时填写）",
            显示选项, key=f"t{题号}", disabled=(状态 != "写完了但做错")
        )
        类型 = [显示转短名[x] for x in 选中的显示]
        if 状态 == "写完了但做错" and not 类型:
            全部通过 = False
            st.caption("⚠️ 请至少选一个错误类型")
        if 状态 != "写完了但做错": 类型 = []

        理由 = st.text_input(f"第{题号}题补充说明（选填）", key=f"r{题号}")
        预判[题号] = {"状态": 状态, "类型": 类型, "卡点描述": 卡点描述, "理由": 理由}
        st.divider()

    if st.button("③ 提交预判，获取 AI 讲评"):
        if not 全部通过:
            st.warning("还有题目没有完成必选项。")
        elif st.session_state.get("正在处理"):
            st.warning("上一次任务还在处理中，请稍候再试。")
        else:
            st.session_state.正在处理 = True
            st.session_state.预判 = 预判

            # ---- 批量讲评：一次调用输出所有题的讲评（快很多） ----
            诊断结果列表 = []
            总题数 = len(st.session_state.识别结果)

            题目列表 = [{
                "题号": 题.get("题号", "?"),
                "题干": 题.get("题干", ""),
                "学生作答": 题.get("学生作答", ""),
                "学生预判": 预判.get(题.get("题号", "?"), {}),
                "关键检查点候选": 题.get("关键检查点", "无"),
            } for 题 in st.session_state.识别结果]

            批量prompt = f"""
你是一位高中数学错题讲评老师。请对下面列表中的【每一道】错题逐一讲评，每道题独立输出一个 JSON 对象，最终输出为一个 JSON 数组（数组顺序与题目列表一致）。

【题目列表】
{json.dumps(题目列表, ensure_ascii=False, indent=1)}

【关于关键检查点的说明】
每道题的“关键检查点候选”只是判卷阶段给出的候选，请先核实它是否属实、是否真的解释了学生的问题：属实才在“解答”中覆盖它；与本题不符或无法确认时，不要强行覆盖，以你自己核实后的判断为准。

【本册范围】{本册范围}
【超纲约束】{超纲约束}
【参考标签】{参考标签}

【输出要求（务必精简，控制篇幅）】
- 每道题的“解答”：用 markdown 列表分步写，公式用 $...$ 包裹，写清关键步骤和最终答案，保证可复算；中间计算步骤用“关键变形”合并，不要逐行展开，一道题解答控制在 10 步以内。
- 其余文字字段一律精简：
  - 错误性质描述：一句话。
  - 判断证据：一句话。
  - 重点提示：一句话。
  - 讲评：不超过 3 句话。
  - 可操作建议：一句话，具体可执行。
- “与学生预判的对照”必须非空，按下面规则写：
  - 学生预判的标签与你的判断一致：写“你选的「X」判断准确，证据支持这一归因：因为Z。”不要写“更准确”之类暗示判断不同的表述。
  - 学生预判的标签与你的判断不一致：写“你选的是X；证据显示更准确的标签是Y，因为Z。”
  - 学生没有选类型：写“你当时没有选类型，AI 判断为Y。”
  - 学生可能选了多个标签，对照时针对与你判断相关的那一个写即可。
- 数学判断必须正确、可复算；不确定时写“此处需要进一步核对”，不要硬下结论。

请输出**单个 JSON 数组**，数组元素为包含以下字段的对象：
- 题号
- 知识点定位（限《本册范围》内的章节）
- 错误性质描述
- 参考标签（数组）
- 判断证据
- 与学生预判的对照
- 解答
- 重点提示
- 讲评
- 可操作建议

只输出 JSON 数组，不要输出任何其他文字。
"""
            with st.spinner(f"正在批量讲评 {总题数} 道题（免费模型较慢，约 2-4 分钟，请耐心等待）..."):
                try:
                    raw = 调用模型带回退(批量prompt, API_KEY, 文本模型链, temperature=0, max_tokens=24000)
                    结果, _ = 解析(raw)
                    结果 = 解包列表(结果)
                    if isinstance(结果, dict):
                        结果 = [结果]
                    if 结果 and isinstance(结果, list):
                        诊断结果列表 = 规范化(结果)
                        for 单题 in 诊断结果列表:
                            if not 单题.get("与学生预判的对照"):
                                单题["与学生预判的对照"] = "（对照生成失败，请参考错误性质和解答理解本题卡点）"
                except Exception as e:
                    st.warning(f"批量讲评失败：{e}，回退为逐题讲评…")

            if not 诊断结果列表:
                # ---- 回退：逐题讲评（批量失败时才走这里） ----
                progress_bar = st.progress(0)
                for idx, 题 in enumerate(st.session_state.识别结果):
                    题号 = 题.get("题号", "?")
                    题干 = 题.get("题干", "")
                    学生作答 = 题.get("学生作答", "")
                    关键检查点 = 题.get("关键检查点", "无")
                    当前预判 = 预判.get(题号, {})
                    预判文本 = json.dumps({题号: 当前预判}, ensure_ascii=False)

                    progress_bar.progress((idx + 1) / 总题数, text=f"正在逐题讲评第 {题号} 题...")

                    prompt = f"""
你是一位高中数学错题讲评老师。请**只针对第 {题号} 题**进行讲评。不要输出其他题目，不要泛泛而谈。

【本题信息】
题干：{题干}
学生作答：{学生作答}
学生预判：{预判文本}
判卷阶段发现的关键检查点候选：{关键检查点}

【关于关键检查点的说明】
上面的“关键检查点”只是判卷阶段给出的候选，请你先核实它是否属实、是否真的解释了学生的问题：
- 若属实，请在“解答”中覆盖它；
- 若与本题不符或无法确认，**不要强行覆盖**，以你自己核实后的判断为准。
宁可如实说明“无法确认”，也不要为了凑检查点而写错内容。

【本册范围】{本册范围}
【超纲约束】{超纲约束}
【参考标签】{参考标签}

【输出要求（务必精简，控制篇幅）】
- “解答”：用 markdown 列表分步写，公式用 $...$ 包裹，写清关键步骤和最终答案，保证可复算；中间计算步骤用“关键变形”合并，不要逐行展开，解答控制在 10 步以内。
- 其余文字字段一律精简：错误性质描述一句话；判断证据一句话；重点提示一句话；讲评不超过 3 句话；可操作建议一句话。
- “与学生预判的对照”必须非空，按下面规则写：
  - 学生预判的标签与你的判断一致：写“你选的「X」判断准确，证据支持这一归因：因为Z。”不要写“更准确”之类暗示判断不同的表述。
  - 学生预判的标签与你的判断不一致：写“你选的是X；证据显示更准确的标签是Y，因为Z。”
  - 学生没有选类型：写“你当时没有选类型，AI 判断为Y。”
  - 学生可能选了多个标签，对照时针对与你判断相关的那一个写即可。
- 数学判断必须正确、可复算；不确定时写“此处需要进一步核对”，不要硬下结论。

请输出**单个 JSON 对象**（不是数组），包含以下字段：
- 题号
- 知识点定位（限《本册范围》内的章节）
- 错误性质描述
- 参考标签（数组）
- 判断证据
- 与学生预判的对照
- 解答
- 重点提示
- 讲评
- 可操作建议

只输出 JSON 对象，不要输出任何其他文字。
"""
                    try:
                        raw = 调用模型带回退(prompt, API_KEY, 文本模型链, temperature=0, max_tokens=8000)
                        结果, _ = 解析(raw)
                        if isinstance(结果, dict):
                            结果 = [结果]
                        if 结果 and isinstance(结果, list) and len(结果) > 0:
                            单题结果 = 规范化(结果)[0]
                            if not 单题结果.get("与学生预判的对照"):
                                单题结果["与学生预判的对照"] = "（对照生成失败，请参考错误性质和解答理解本题卡点）"
                            诊断结果列表.append(单题结果)
                        else:
                            st.warning(f"第 {题号} 题讲评解析失败，已跳过。原始返回：{raw[:100]}...")
                    except Exception as e:
                        st.error(f"第 {题号} 题讲评调用出错：{e}")
                progress_bar.empty()

            if 诊断结果列表:
                st.session_state.正在处理 = False
                st.session_state.诊断结果 = 诊断结果列表
                st.session_state.最终归因 = None
                刷新()
            else:
                st.session_state.正在处理 = False
                st.error("所有题目讲评均失败，请检查网络或 API Key。")

# ========== 第3步：对照 + 修正 ==========
if st.session_state.get("诊断结果"):
    st.subheader("④ 对照与修正")
    最终归因 = {}
    for 题 in st.session_state.诊断结果:
        题号 = 题.get("题号", "?")
        学生预判 = (st.session_state.预判 or {}).get(题号, {})
        with st.expander(f"第 {题号} 题 ｜ {题.get('知识点定位','')}", expanded=True):
            st.write(f"**你当时的情况**：{学生预判.get('状态','')}")
            if 学生预判.get("卡点描述"): st.write(f"**你当时卡在**：{学生预判.get('卡点描述')}")
            if 学生预判.get("类型"): st.write(f"**你当时选的类型**：{'、'.join(学生预判.get('类型', []))}")
            st.write(f"**错误性质**：{题.get('错误性质描述','')}")
            st.write(f"**参考标签**：{'、'.join(题.get('参考标签', []))}")
            st.write(f"**判断证据**：{题.get('判断证据','')}")
            st.info(f"**对照**：{题.get('与学生预判的对照','')}")
            st.markdown(f"**解答**：\n\n{题.get('解答','')}")
            st.warning(f"**重点提示**：{题.get('重点提示','')}")
            st.write(f"**讲评**：{题.get('讲评','')}")
            st.success(f"**建议**：{题.get('可操作建议','')}")

            # 默认选中改为 AI 的归因（参考标签），而不是学生预判
            AI短名 = 题.get("参考标签", [])
            if isinstance(AI短名, str):
                AI短名 = [AI短名]
            default_显示 = [短名转显示[t] for t in AI短名 if t in 短名转显示]
            选中的显示 = st.multiselect(f"第{题号}题你最终确认的归因", 显示选项, default=default_显示, key=f"f{题号}")
            最终归因[题号] = [显示转短名[x] for x in 选中的显示]

    if st.button("保存最终归因"):
        st.session_state.最终归因 = 最终归因
        st.success("你的最终归因已保存，本阶段流程结束。")
