from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "backend_test" / "intent" / "test_data" / "user_batch_v1"


FALSE_UNSUPPORTED = {
    "file_write_request": False,
    "file_delete_request": False,
    "kb_admin_request": False,
    "privileged_operation": False,
    "unknown_external_action": False,
}

DEP_NONE = {
    "none": True,
    "history_reference": False,
    "previous_answer": False,
    "previous_retrieval": False,
    "ambiguous": False,
}
DEP_HISTORY = {
    "none": False,
    "history_reference": True,
    "previous_answer": False,
    "previous_retrieval": False,
    "ambiguous": False,
}
DEP_PREV_ANSWER = {
    "none": False,
    "history_reference": False,
    "previous_answer": True,
    "previous_retrieval": False,
    "ambiguous": False,
}
DEP_AMBIG = {
    "none": False,
    "history_reference": False,
    "previous_answer": False,
    "previous_retrieval": False,
    "ambiguous": True,
}

CONTRACT_HISTORY = [
    {"role": "user", "content": "合同无效之后违约责任还要不要承担？"},
    {"role": "assistant", "content": "我刚才解释过合同无效、违约责任和缔约过失责任的基本区别。"},
]
MEDICAL_HISTORY = [
    {"role": "user", "content": "医疗事故责任和一般医疗风险怎么区分？"},
    {"role": "assistant", "content": "我刚才已经说明了医疗事故认定通常要看过错、损害结果和因果关系。"},
]
COMP_HISTORY = [
    {"role": "user", "content": "解除劳动合同后经济补偿一般怎么算？"},
    {"role": "assistant", "content": "我刚才先按常见经济补偿规则解释了一遍。"},
]
QA_HISTORY = [
    {"role": "user", "content": "刚才那段合同规则我还想继续问。"},
    {"role": "assistant", "content": "可以，我们继续围绕合同责任来讨论。"},
]
META_HISTORY = [
    {"role": "user", "content": "你刚才说合同无效要分情形判断。"},
    {"role": "assistant", "content": "是的，我刚才根据民法典合同编的规则做了一个概括。"},
]


def modifiers(**kwargs):
    base = {
        "follow_up": False,
        "challenge": False,
        "ask_source": False,
        "ask_capability": False,
        "needs_clarification": False,
        "out_of_scope": False,
    }
    base.update(kwargs)
    return base


def sample(
    *,
    sid: str,
    batch: str,
    query: str,
    history: list[dict[str, str]],
    classifier_mode: str,
    required_signals: list[str],
    required_rule_ids: list[str],
    rule_expectations: dict[str, bool],
    dependency_signals: dict[str, bool],
    main_intent: str,
    mod: dict[str, bool],
    complexity: str,
    shape: str,
    context_dependency: str,
    route: str,
    mode: str,
    notes: str,
    unsupported_signals: dict[str, bool] | None = None,
) -> dict:
    return {
        "id": sid,
        "batch": batch,
        "input": {
            "user_query": query,
            "history": history,
        },
        "gold": {
            "evidence": {
                "classifier_mode": classifier_mode,
                "required_signals": required_signals,
                "required_rule_ids": required_rule_ids,
                "rule_expectations": rule_expectations,
                "unsupported_signals": unsupported_signals or FALSE_UNSUPPORTED,
                "dependency_signals": dependency_signals,
            },
            "resolved": {
                "main_intent": main_intent,
                "modifiers": mod,
                "task": {
                    "complexity": complexity,
                    "shape": shape,
                },
                "context_dependency": context_dependency,
            },
            "control": {
                "route": route,
                "mode": mode,
            },
        },
        "notes": notes,
    }


def build_standard_qa() -> list[dict]:
    queries = [
        ("根据民法典，合同无效的情形有哪些？", "标准法律知识问答", ["intent.qa.domain"], {"intent.qa.domain": True, "intent.chat.greeting": False, "task.enumerated_questions": False}),
        ("医疗过失责任的构成要件是什么？", "标准医疗法律问答", ["intent.qa.domain"], {"intent.qa.domain": True, "challenge.disagree": False}),
        ("高血压的诊断标准是多少？", "标准医学问答", ["intent.qa.domain"], {"intent.qa.domain": True, "system.capability.ask": False}),
        ("医保报销比例如何计算？", "领域问答但关键词不一定稳定命中", [], {"intent.qa.domain": False, "task.complex.request": False}),
        ("侵犯著作权需要承担哪些法律责任？", "知识产权法律问答", ["intent.qa.domain"], {"intent.qa.domain": True}),
        ("刑事拘留最长多少天？", "法律问答短句", [], {"intent.qa.domain": False, "task.enumerated_questions": False}),
        ("糖尿病并发症包括哪些？", "疾病知识问答", [], {"intent.qa.domain": False, "task.enumerated_questions": False}),
        ("电子合同是否具有法律效力？", "法律效力问答", ["intent.qa.domain"], {"intent.qa.domain": True}),
        ("什么是非法行医？", "定义型问答", [], {"intent.qa.domain": False}),
        ("公司破产清算流程是怎样的？", "流程型法律问答", ["intent.qa.domain"], {"intent.qa.domain": True}),
    ]
    rows = []
    for idx, (query, notes, rules, expectations) in enumerate(queries, start=1):
        rows.append(
            sample(
                sid=f"user_batch_standard_qa_{idx:03d}",
                batch="standard_qa",
                query=query,
                history=[],
                classifier_mode="rule_plus_model",
                required_signals=["qa"],
                required_rule_ids=rules,
                rule_expectations=expectations,
                dependency_signals=DEP_NONE,
                main_intent="qa",
                mod=modifiers(),
                complexity="simple",
                shape="single_question",
                context_dependency="none",
                route="rag",
                mode="normal",
                notes=notes,
            )
        )
    return rows


def build_fuzzy_qa() -> list[dict]:
    queries = [
        ("我这种情况算违法吗？", "信息不足的法律判断"),
        ("这样算不算医疗事故？", "信息不足的医疗责任判断"),
        ("这个要赔钱吗？", "赔偿判断缺事实"),
        ("医院这么做合理吗？", "医疗场景但缺事实"),
        ("这种合同有效吗？", "合同效力判断缺事实"),
        ("这算重大疾病吗？", "医学判断缺上下文"),
        ("这种药可以长期吃吗？", "用药建议缺具体药物信息"),
        ("这个情况法院会怎么判？", "裁判结果预测缺事实"),
        ("这样会被拘留吗？", "刑事后果判断缺事实"),
        ("这种属于侵权吗？", "侵权判断缺事实"),
    ]
    rows = []
    for idx, (query, notes) in enumerate(queries, start=1):
        rows.append(
            sample(
                sid=f"user_batch_fuzzy_qa_{idx:03d}",
                batch="fuzzy_qa",
                query=query,
                history=[],
                classifier_mode="model_first_with_rule_guard",
                required_signals=["qa", "needs_clarification"],
                required_rule_ids=[],
                rule_expectations={"intent.qa.domain": False, "challenge.disagree": False},
                dependency_signals=DEP_AMBIG,
                main_intent="qa",
                mod=modifiers(needs_clarification=True),
                complexity="simple",
                shape="single_question",
                context_dependency="ambiguous",
                route="direct",
                mode="clarify",
                notes=notes,
            )
        )
    return rows


def build_chat() -> list[dict]:
    queries = [
        ("你今天状态怎么样？", "轻闲聊"),
        ("最近压力有点大。", "情绪表达"),
        ("你觉得人为什么会焦虑？", "开放闲聊"),
        ("聊聊吧。", "邀请闲聊"),
        ("你是谁？", "身份式闲聊"),
        ("哈哈哈。", "情绪回应"),
        ("有点烦。", "情绪倾诉"),
        ("你会不会累？", "拟人闲聊"),
        ("今天天气不错。", "日常寒暄"),
        ("推荐一本书。", "泛化闲聊请求"),
    ]
    rows = []
    for idx, (query, notes) in enumerate(queries, start=1):
        rows.append(
            sample(
                sid=f"user_batch_chat_{idx:03d}",
                batch="chat",
                query=query,
                history=[],
                classifier_mode="model_first_with_rule_guard",
                required_signals=["chat"],
                required_rule_ids=[],
                rule_expectations={"intent.chat.greeting": False, "intent.qa.domain": False},
                dependency_signals=DEP_NONE,
                main_intent="chat",
                mod=modifiers(),
                complexity="simple",
                shape="none",
                context_dependency="none",
                route="chat",
                mode="normal",
                notes=notes,
            )
        )
    return rows


def build_meta() -> list[dict]:
    rows = [
        sample(sid="user_batch_meta_001", batch="meta", query="你刚才的依据是什么？", history=META_HISTORY, classifier_mode="rule_plus_model", required_signals=["ask_source"], required_rule_ids=["source.ask_basis"], rule_expectations={"source.ask_basis": True, "challenge.disagree": False, "system.capability.ask": False}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(ask_source=True), complexity="simple", shape="single_question", context_dependency="previous_answer", route="rag", mode="normal", notes="追问依据"),
        sample(sid="user_batch_meta_002", batch="meta", query="你确定吗？", history=META_HISTORY, classifier_mode="rule_only", required_signals=["challenge"], required_rule_ids=["challenge.disagree"], rule_expectations={"challenge.disagree": True, "source.ask_basis": False}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="直接质疑"),
        sample(sid="user_batch_meta_003", batch="meta", query="这个结论不对吧？", history=META_HISTORY, classifier_mode="rule_only", required_signals=["challenge"], required_rule_ids=["challenge.disagree"], rule_expectations={"challenge.disagree": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="明确否定上一轮结论"),
        sample(sid="user_batch_meta_004", batch="meta", query="你是根据哪条法律说的？", history=META_HISTORY, classifier_mode="rule_plus_model", required_signals=["ask_source"], required_rule_ids=["source.ask_basis"], rule_expectations={"source.ask_basis": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(ask_source=True), complexity="simple", shape="single_question", context_dependency="previous_answer", route="rag", mode="normal", notes="索取法条依据"),
        sample(sid="user_batch_meta_005", batch="meta", query="有出处吗？", history=META_HISTORY, classifier_mode="rule_plus_model", required_signals=["ask_source"], required_rule_ids=["source.ask_basis"], rule_expectations={"source.ask_basis": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(ask_source=True), complexity="simple", shape="single_question", context_dependency="previous_answer", route="rag", mode="normal", notes="索取出处"),
        sample(sid="user_batch_meta_006", batch="meta", query="你是不是编的？", history=META_HISTORY, classifier_mode="rule_only", required_signals=["challenge"], required_rule_ids=["challenge.disagree"], rule_expectations={"challenge.disagree": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="强质疑"),
        sample(sid="user_batch_meta_007", batch="meta", query="你支持哪些法律版本？", history=[], classifier_mode="rule_only", required_signals=["system", "ask_capability"], required_rule_ids=["system.capability.ask"], rule_expectations={"system.capability.ask": True, "intent.qa.domain": False}, dependency_signals=DEP_NONE, main_intent="system", mod=modifiers(ask_capability=True), complexity="simple", shape="none", context_dependency="none", route="direct", mode="capability", notes="问系统能力范围"),
        sample(sid="user_batch_meta_008", batch="meta", query="你能查到最新司法解释吗？", history=[], classifier_mode="rule_only", required_signals=["system", "ask_capability"], required_rule_ids=["system.capability.ask"], rule_expectations={"system.capability.ask": True}, dependency_signals=DEP_NONE, main_intent="system", mod=modifiers(ask_capability=True), complexity="simple", shape="none", context_dependency="none", route="direct", mode="capability", notes="问系统能力边界"),
        sample(sid="user_batch_meta_009", batch="meta", query="你的回答有证据吗？", history=META_HISTORY, classifier_mode="rule_plus_model", required_signals=["ask_source"], required_rule_ids=["source.ask_basis"], rule_expectations={"source.ask_basis": True, "challenge.disagree": False}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(ask_source=True), complexity="simple", shape="single_question", context_dependency="previous_answer", route="rag", mode="normal", notes="追问证据"),
        sample(sid="user_batch_meta_010", batch="meta", query="你是不是搞错了？", history=META_HISTORY, classifier_mode="rule_only", required_signals=["challenge"], required_rule_ids=["challenge.disagree"], rule_expectations={"challenge.disagree": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="质疑回答正确性"),
    ]
    return rows


def build_follow_up() -> list[dict]:
    items = [
        ("那这种情况呢？", CONTRACT_HISTORY, "典型追问"),
        ("如果是公司呢？", CONTRACT_HISTORY, "条件变体追问"),
        ("那医疗领域也是这样吗？", QA_HISTORY, "跨领域追问"),
        ("那严重一点会怎样？", MEDICAL_HISTORY, "结果追问"),
        ("如果是未成年人呢？", CONTRACT_HISTORY, "主体变体追问"),
        ("那换成刑事责任呢？", CONTRACT_HISTORY, "责任类型切换"),
        ("这种情况赔多少？", COMP_HISTORY, "金额追问"),
        ("那法院一般怎么处理？", CONTRACT_HISTORY, "裁判倾向追问"),
        ("那如果没有证据呢？", META_HISTORY, "证据条件追问"),
        ("那这个标准是全国统一的吗？", MEDICAL_HISTORY, "标准范围追问"),
    ]
    rows = []
    for idx, (query, history, notes) in enumerate(items, start=1):
        rows.append(
            sample(
                sid=f"user_batch_follow_up_{idx:03d}",
                batch="follow_up",
                query=query,
                history=history,
                classifier_mode="rule_plus_model",
                required_signals=["follow_up"],
                required_rule_ids=["context.follow_up.reference"],
                rule_expectations={"context.follow_up.reference": True, "challenge.disagree": False},
                dependency_signals=DEP_HISTORY,
                main_intent="qa",
                mod=modifiers(follow_up=True),
                complexity="simple",
                shape="single_question",
                context_dependency="history_reference",
                route="rag",
                mode="normal",
                notes=notes,
            )
        )
    return rows


def build_mixed() -> list[dict]:
    return [
        sample(sid="user_batch_mixed_001", batch="mixed_intent", query="你刚才说合同无效，那依据是什么？是不是你理解错了？", history=CONTRACT_HISTORY, classifier_mode="rule_plus_model", required_signals=["challenge", "ask_source"], required_rule_ids=["source.ask_basis", "challenge.disagree"], rule_expectations={"source.ask_basis": True, "challenge.disagree": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True, ask_source=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="质疑与索引依据同时出现"),
        sample(sid="user_batch_mixed_002", batch="mixed_intent", query="医疗事故是不是都要赔钱？感觉不合理啊。", history=MEDICAL_HISTORY, classifier_mode="rule_plus_model", required_signals=["challenge"], required_rule_ids=["challenge.disagree"], rule_expectations={"challenge.disagree": True, "intent.qa.domain": False}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="事实问答加态度质疑"),
        sample(sid="user_batch_mixed_003", batch="mixed_intent", query="你确定这是最新法律吗？我查的好像不一样。", history=META_HISTORY, classifier_mode="rule_only", required_signals=["challenge"], required_rule_ids=["challenge.disagree"], rule_expectations={"challenge.disagree": True, "source.ask_basis": False}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(challenge=True), complexity="simple", shape="verify", context_dependency="previous_answer", route="rag", mode="challenge", notes="版本一致性质疑"),
        sample(sid="user_batch_mixed_004", batch="mixed_intent", query="那这种情况是不是违法？如果不是为什么？", history=CONTRACT_HISTORY, classifier_mode="rule_plus_model", required_signals=["follow_up", "multi_question"], required_rule_ids=["context.follow_up.reference", "task.enumerated_questions"], rule_expectations={"context.follow_up.reference": True, "task.enumerated_questions": True}, dependency_signals=DEP_HISTORY, main_intent="qa", mod=modifiers(follow_up=True), complexity="compound", shape="multi_question", context_dependency="history_reference", route="rag", mode="normal", notes="追问加双问题"),
        sample(sid="user_batch_mixed_005", batch="mixed_intent", query="如果医生误诊，但不是故意的，责任怎么算？", history=[], classifier_mode="rule_plus_model", required_signals=["qa"], required_rule_ids=["intent.qa.domain"], rule_expectations={"intent.qa.domain": True, "task.complex.request": False}, dependency_signals=DEP_NONE, main_intent="qa", mod=modifiers(), complexity="simple", shape="single_question", context_dependency="none", route="rag", mode="normal", notes="带条件的责任问答"),
        sample(sid="user_batch_mixed_006", batch="mixed_intent", query="你能简单说一下，然后给出法律依据吗？", history=CONTRACT_HISTORY, classifier_mode="rule_plus_model", required_signals=["ask_source", "multi_question"], required_rule_ids=["source.ask_basis", "task.enumerated_questions"], rule_expectations={"source.ask_basis": True, "task.enumerated_questions": True, "system.capability.ask": False}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(ask_source=True), complexity="compound", shape="multi_question", context_dependency="previous_answer", route="rag", mode="normal", notes="回答方式加索引依据"),
        sample(sid="user_batch_mixed_007", batch="mixed_intent", query="这算侵权吧？还是只是违约？", history=[], classifier_mode="model_first_with_rule_guard", required_signals=["qa", "complex"], required_rule_ids=[], rule_expectations={"task.complex.request": False, "task.enumerated_questions": True}, dependency_signals=DEP_NONE, main_intent="qa", mod=modifiers(), complexity="complex", shape="compare", context_dependency="none", route="agent", mode="normal", notes="比较型法律判断"),
        sample(sid="user_batch_mixed_008", batch="mixed_intent", query="那这种是不是既违法又要赔偿？", history=CONTRACT_HISTORY, classifier_mode="rule_plus_model", required_signals=["follow_up"], required_rule_ids=["context.follow_up.reference"], rule_expectations={"context.follow_up.reference": True, "task.enumerated_questions": False}, dependency_signals=DEP_HISTORY, main_intent="qa", mod=modifiers(follow_up=True), complexity="compound", shape="multi_question", context_dependency="history_reference", route="rag", mode="normal", notes="追问且同时问违法与赔偿"),
        sample(sid="user_batch_mixed_009", batch="mixed_intent", query="你说的赔偿比例有数据支持吗？", history=COMP_HISTORY, classifier_mode="rule_plus_model", required_signals=["ask_source"], required_rule_ids=["source.ask_basis"], rule_expectations={"source.ask_basis": True}, dependency_signals=DEP_PREV_ANSWER, main_intent="qa", mod=modifiers(ask_source=True), complexity="simple", shape="single_question", context_dependency="previous_answer", route="rag", mode="normal", notes="追问数据依据"),
        sample(sid="user_batch_mixed_010", batch="mixed_intent", query="如果合同里写了免责条款，那还有效吗？", history=[], classifier_mode="rule_plus_model", required_signals=["qa"], required_rule_ids=["intent.qa.domain"], rule_expectations={"intent.qa.domain": True}, dependency_signals=DEP_NONE, main_intent="qa", mod=modifiers(), complexity="simple", shape="single_question", context_dependency="none", route="rag", mode="normal", notes="带条件的合同效力问答"),
    ]


def build_adversarial() -> list[dict]:
    items = [
        ("根据你刚才说的逻辑，这是不是说明法律是随便解释的？", META_HISTORY, "对系统推理方式的对抗性质疑"),
        ("所以你其实也不确定？", META_HISTORY, "质疑回答确定性"),
        ("那你为什么之前说一定要赔？", COMP_HISTORY, "针对前后不一致的挑战"),
        ("这是不是系统胡说八道？", META_HISTORY, "攻击性挑战"),
        ("如果法律都能这样理解，那还有什么意义？", META_HISTORY, "对解释一致性的对抗性追问"),
    ]
    rows = []
    for idx, (query, history, notes) in enumerate(items, start=1):
        rows.append(
            sample(
                sid=f"user_batch_adversarial_{idx:03d}",
                batch="adversarial",
                query=query,
                history=history,
                classifier_mode="rule_only",
                required_signals=["challenge"],
                required_rule_ids=["challenge.disagree"],
                rule_expectations={"challenge.disagree": True},
                dependency_signals=DEP_PREV_ANSWER,
                main_intent="qa",
                mod=modifiers(challenge=True),
                complexity="simple",
                shape="verify",
                context_dependency="previous_answer",
                route="rag",
                mode="challenge",
                notes=notes,
            )
        )
    return rows


def build_long_case_complex() -> list[dict]:
    items = [
        ("我父亲在医院做手术，术后感染，医生说是正常并发症，但后来病情恶化，我们认为是医院消毒不到位导致的。医院拒绝赔偿，说我们无法证明因果关系。请问这种情况是否属于医疗过错？责任如何认定？", "医疗事实链长，要求责任认定", True),
        ("我和公司签了三年劳动合同，现在公司单方面解除，说我绩效不达标，但合同里没有具体绩效标准。请问这种解除是否合法？", "劳动争议事实判断", True),
        ("患者长期服用某种降压药出现肝功能异常，医生未及时提醒风险。是否构成医疗过失？", "医疗过失事实认定", True),
        ("我在电商平台买到假货，平台说他们只是提供交易服务，请问平台是否需要承担连带责任？", "平台责任归责判断", False),
        ("医院误诊延误治疗三个月，导致病情加重，但医生称属于误判而非过失，这种情况下如何判断责任？", "医疗误诊责任判断", True),
    ]
    rows = []
    for idx, (query, notes, qa_rule_expected) in enumerate(items, start=1):
        rows.append(
            sample(
                sid=f"user_batch_long_case_complex_{idx:03d}",
                batch="long_case_complex",
                query=query,
                history=[],
                classifier_mode="model_first_with_rule_guard",
                required_signals=["qa", "complex"],
                required_rule_ids=[],
                rule_expectations={"intent.qa.domain": qa_rule_expected, "task.complex.request": False},
                dependency_signals=DEP_NONE,
                main_intent="qa",
                mod=modifiers(),
                complexity="complex",
                shape="verify",
                context_dependency="none",
                route="agent",
                mode="normal",
                notes=notes,
            )
        )
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    datasets = {
        "standard_qa.json": build_standard_qa(),
        "fuzzy_qa.json": build_fuzzy_qa(),
        "chat.json": build_chat(),
        "meta.json": build_meta(),
        "follow_up.json": build_follow_up(),
        "mixed_intent.json": build_mixed(),
        "adversarial.json": build_adversarial(),
        "long_case_complex.json": build_long_case_complex(),
    }
    readme = """# user_batch_v1

这批数据直接来自本轮讨论中的 8 类 query，目标不是回归已有规则，而是用更贴近真实表达的输入去压测 `input -> evidence -> resolved -> control` 四层识别效果。

批次包括：
- `standard_qa`
- `fuzzy_qa`
- `chat`
- `meta`
- `follow_up`
- `mixed_intent`
- `adversarial`
- `long_case_complex`

其中：
- `standard_qa` 主要测清晰问答
- `fuzzy_qa` 主要测 `needs_clarification`
- `mixed_intent` 主要测 modifier 组合与 resolver 收敛
- `adversarial` 主要测 challenge 稳健性
- `long_case_complex` 主要测复杂事实输入是否会掉进简单流
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    for filename, rows in datasets.items():
        (OUT_DIR / filename).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(rows) for rows in datasets.values())
    print(f"Generated {total} samples in {OUT_DIR}")


if __name__ == "__main__":
    main()
