import streamlit as st
import base64, json, requests, ast, time, os
from collections import Counter

# ==================== 在这里填写你的智谱 API Key ====================
# 本机运行：在 .streamlit/secrets.toml 里写 ZHIPU_API_KEY = "你的Key"
# 云端运行：在 Streamlit Cloud 的 Secrets 里填 ZHIPU_API_KEY
API_KEY = st.secrets["ZHIPU_API_KEY"]
# ====================================================================

# ==================== 免费模型配置（2026-11 智谱免费档） ====================
# 视觉识别（只读图抽文字）：glm-4.6v-flash（免费）
# 判卷 + 讲评（数学推理）：glm-4.7-flash（免费文本模型，推理远强于视觉 flash）
MODEL_VISION = "glm-4.6v-flash"
MODEL_REASON = "glm-4.7-flash"
TEMPERATURE  = 0.0   # 判卷/讲评用低温度，减少随机性
# 提示：免费模型有速率限制（RPM/RPD），演示逐题讲评时会依次调用，
# 429 已自动退避重试；若经常触发，可在【讲评循环】里加 time.sleep(1)。
# ====================================================================

st.set_page_config(page_title="数学试卷讲评 Demo", layout="wide")
st.title("数学试卷 AI 讲评 Demo")

# ========== 内置卷子库（明天加手写卷就在下面加一行） ==========
内置卷子库 = {
    "样卷 1：沪教版必修一模拟卷（电脑排版）": "builtin_papers/paper_1.jpg",
    # "样卷 2：手写卷": "builtin_papers/handwriting_1.jpg",
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
def 调用模型(prompt, key, model, img_b64=None, mime=None, temperature=TEMPERATURE, max_retries=4):
    """统一调用智谱 API。img_b64 传了就按多模态（图片+文本），否则纯文本。"""
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
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            if r.status_code == 429:
                time.sleep((attempt + 1) * 15)
                continue
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw
                raw = raw.rsplit("```", 1)[0]
            return raw.strip()
        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
    raise Exception("限流持续，请等待后重试")

def 解析(raw):
    try: return json.loads(raw), None
    except: pass
    try: return ast.literal_eval(raw), None
    except: return None, raw

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

# ========== 侧边栏 ==========
教材 = st.sidebar.selectbox("选择教材范围", 教材选项)
知识点体系 = 知识点体系库[教材]

# ========== 图片来源：上传 or 内置 ==========
st.subheader("选择试卷")
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

# ========== 第1步：识别 + 判卷（两阶段，读图与推理分离） ==========
if st.button("① 识别并判卷"):
    if 图片字节 is None:
        st.warning("请先选择或上传试卷图片")
    else:
        img_b64 = base64.b64encode(图片字节).decode()
        mime = 图片类型

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
- 数学公式用线性文本表达，例如：f(x)=sqrt(x-1)+1/(x-2)、x^2-3x+2≤0、log2(x)≥1、|x-1|≤2、x^2+bx+c、a≠0、Δ=b^2-4ac。

输出 JSON 数组，每项只含 题号、题干、学生作答 三个字段。只输出 JSON，不要输出任何其他文字。
"""
        with st.spinner("① 视觉识别：正在读取卷面文字..."):
            raw = 调用模型(识别prompt, API_KEY, model=MODEL_VISION, img_b64=img_b64, mime=mime)
            识别结果, 原始 = 解析(raw)
        if not 识别结果 or not isinstance(识别结果, list):
            st.session_state.原始文本 = 原始
            st.warning("识别阶段返回非 JSON，原始内容如下：")
            st.code(原始)
            st.stop()

        # ---- 阶段二：文本判卷（免费文本模型，独立解题后与学生作答比较） ----
        判卷prompt = f"""
你是高中数学阅卷老师。下面是刚从试卷照片中识别出来的题目和学生作答（识别可能有少量误差，以你能读到的内容为准）。

【题目列表】
{json.dumps(识别结果, ensure_ascii=False, indent=1)}

【本册范围】{本册范围}
【知识点体系】{知识点体系}
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
        with st.spinner("② 判卷：AI 正在独立解题并与学生作答比较（含复核）..."):
            raw2 = 调用模型(判卷prompt, API_KEY, model=MODEL_REASON)
            判卷列表, 原始2 = 解析(raw2)
        if not 判卷列表 or not isinstance(判卷列表, list):
            st.session_state.原始文本 = 原始2
            st.warning("判卷阶段返回非 JSON，原始内容如下：")
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
        else:
            st.session_state.预判 = 预判

            # 逐题调用（纯文本讲评，不再传图片；关键检查点降级为“候选”）
            诊断结果列表 = []
            progress_bar = st.progress(0)
            总题数 = len(st.session_state.识别结果)

            for idx, 题 in enumerate(st.session_state.识别结果):
                题号 = 题.get("题号", "?")
                题干 = 题.get("题干", "")
                学生作答 = 题.get("学生作答", "")
                关键检查点 = 题.get("关键检查点", "无")
                当前预判 = 预判.get(题号, {})
                预判文本 = json.dumps({题号: 当前预判}, ensure_ascii=False)

                progress_bar.progress((idx + 1) / 总题数, text=f"正在讲评第 {题号} 题...")

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
【知识点体系】{知识点体系}
【超纲约束】{超纲约束}
【参考标签】{参考标签}

【强制要求】
1. “解答”必须用 markdown 有序或无序列表分步写，公式用 $...$ 包裹，数学判断必须正确、可复算；不确定时写“此处需要进一步核对”，不要硬下结论。
2. “与学生预判的对照”字段必须非空。格式固定为：“你选的是X；证据显示更准确的标签是Y，因为Z。”如果学生没选类型，写“你当时没有选类型，AI 判断为Y。”

请输出**单个 JSON 对象**（不是数组），包含以下字段：
- 题号
- 知识点定位
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
                    raw = 调用模型(prompt, API_KEY, model=MODEL_REASON, temperature=0)
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
                st.session_state.诊断结果 = 诊断结果列表
                st.session_state.最终归因 = None
                刷新()
            else:
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
