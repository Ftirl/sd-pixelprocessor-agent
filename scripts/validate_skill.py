#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
VERSION_EXPECTED = "2.5.0"
SPEC = ROOT / "references" / f"SD_PixelProcessor_AGENT_SPEC_v{VERSION_EXPECTED}.md"
WHILE_REF = ROOT / "references" / f"WHILE_OFFICIAL_BASELINE_v{VERSION_EXPECTED}.md"

required = [
    ROOT / "SKILL.md",
    ROOT / "VERSION",
    SPEC,
    ROOT / "references" / "REAL_PROJECT_VALIDATION.md",
    ROOT / "references" / "MORPHING_RETEST_GATES.md",
    ROOT / "references" / "SUN_SHOWER_RETEST_GATES.md",
    ROOT / "references" / "DESCENTE_INFINIE_RETEST_GATES.md",
    ROOT / "scripts" / "project_validation.py",
    ROOT / "scripts" / "layout_intelligence.py",
    ROOT / "references" / f"SD_BUILTIN_FUNCTIONS_v{VERSION_EXPECTED}.md",
    ROOT / "references" / f"NATIVE_PROBE_RESULTS_v{VERSION_EXPECTED}.md",
    WHILE_REF,
    ROOT / "agents" / "openai.yaml",
    ROOT / "scripts" / "lookup_sd_function.py",
    ROOT / "scripts" / "probe_sd_semantics.py",
    ROOT / "references" / f"SD_LIBRARY_FUNCTIONS_v{VERSION_EXPECTED}.md",
    ROOT / "references" / f"library_functions_v{VERSION_EXPECTED}.json",
    ROOT / "scripts" / "dump_library_functions.py",
    ROOT / "scripts" / "verify_library_functions.py",
    ROOT / "scripts" / "render_library_catalog.py",
    ROOT / "scripts" / "runtime_safety.py",
    ROOT / "scripts" / "check_compatibility.py",
    ROOT / "scripts" / "verify_probe_report.py",
    ROOT / "scripts" / "eval_release.py",
    ROOT / "scripts" / "build_manifest.py",
    ROOT / "references" / f"COMPATIBILITY_MATRIX_v{VERSION_EXPECTED}.md",
    ROOT / "references" / f"compatibility_matrix_v{VERSION_EXPECTED}.json",
    ROOT / "references" / f"PRODUCTION_HARDENING_v{VERSION_EXPECTED}.md",
    ROOT / "evals" / "test_runtime_safety.py",
    ROOT / "evals" / "test_release_policy.py",
    ROOT / "evals" / "test_runtime_semantics.py",
    ROOT / "scripts" / "runtime_semantics.py",
    ROOT / "scripts" / "layout_intelligence.py",
    ROOT / "scripts" / "project_validation.py",
    ROOT / "evals" / "test_project_validation.py",
    ROOT / "references" / f"RUNTIME_SEMANTICS_BASELINE_v{VERSION_EXPECTED}.md",
]

errors = []
for path in required:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")

if not errors:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", skill, re.S)
    if not m:
        errors.append("SKILL.md is missing YAML frontmatter")
    else:
        front = m.group(1)
        if not re.search(r"(?m)^name:\s*sd-pixelprocessor-agent\s*$", front):
            errors.append("frontmatter name is missing or incorrect")
        if not re.search(r"(?m)^description:\s*\S", front):
            errors.append("frontmatter description is missing")

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    spec = SPEC.read_text(encoding="utf-8")
    while_ref = WHILE_REF.read_text(encoding="utf-8")
    if version != VERSION_EXPECTED:
        errors.append(f"unexpected VERSION: {version!r}")

    spec_anchors = [
        "SOP-0A", "SOP-3A", "N18", "N23", "N24", "N25", "N26",
        "I26", "I31", "I32", "I33", "I34", "I35", "I36", "I37", "I38", "I39", "I40", "A10", "A11", "A12",
        "SOP-5B", "POSTHOC_EXTRACTION", "POSTHOC_LAYOUT",
        "SOP-5B 阶段锁", "7.5.5 GLSL 未初始化分量",
        "L16：规划排布先于生成（plan-then-generate）",
        "模式 A（新建/移植，默认）",
        "7.5.1 乘法节点选择：`mul` / `mulscalar`（强制表，实测语料）",
        "11.8 乘法节点（`mul`/`mulscalar`）实测语料",
        "端口标识（16.0.3 回读：务必区分\"代码 id\"与\"软件内标识/标签\"）",
        "T40", "T41", "T42", "T43", "T44", "T45", "T46", "T47",
        "7.5.2 角度与向量组装：`atan2` / `vector2` / `cartesian`（官方语义）",
        "7.5.3 数值语义：`mod`/`fmod`/`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep`（两源查证）",
        "11.9 角度与向量组装节点（`atan2`/`vector2`/`cartesian`）实测",
        "11.10 内建函数供给与数值语义实测",
        "11.11 原生数值实测基线",
        "11.12 内建库函数实现图逐节点核对",
        "SOP-0B：原生数值探针",
        "不需要像通常的 atan2 函数那样交换 x 和 y",
        "N27", "N28", "I41", "D35",
        "SD_BUILTIN_FUNCTIONS_v2.5.0.md",
        "NATIVE_PROBE_RESULTS_v2.5.0.md",
        "SD_LIBRARY_FUNCTIONS_v2.5.0.md",
        "library_functions_v2.5.0.json",
        "dump_library_functions.py",
        "verify_library_functions.py",
        "render_library_catalog.py",
        "getInputPropertyNode",
        "distance_vec3",
        "input_v",
        "float32",
        "probe_sd_semantics.py",
        "lookup_sd_function.py",
        "Rounds up when decimal is greater or equal than 0.5",
        "same sign as a",
        "If X == 0, returns 1",
        "mod(−0.25,1)=0.75",
        "静默",
        "newPropertyGraph",
        "exportSDGraphOutputs",
        "7.9.11 循环体函数化与 While 连接",
        "Statement 模式", "Set/Sequence 值边界",
        "W1 — 执行顺序", "W4 — 分支节点隔离", "W8 — Pixel Processor 中的意义",
        "W11 — 所有源码循环格式统一降级为 While",
        "W12 — While 连接规划是交付物的一部分",
        "W15 — 循环内状态 Get 的后分支连通性与数值验证",
        "W16 — 跨度按语句与深度归一化，不设绝对高度墙",
        "7.9.3 While 连接规划（端口级）", "7.9.8 例外：允许 unroll 的条件",
        "7.9.10 标准 While 连接模板（推荐连接方式，模板文件实测）",
        "7.10 语句树连接方式与跨度/节点预算（Set → Statement Sequence → Value Spine → Pure Terminal）",
        "7.10.4 跨度预算（归一化，替代绝对高度墙）",
        "7.10.5 节点数量预算（重写）",
        "L14：跨度预算按语句带数与表达式深度归一化",
        "L15：禁止跨带长连线（读取走上游 Get）",
        "11.7 语句树连接与跨度实测基线",
        "0372b50801013d2ae1be57806778a8799223042e7bd57429caaf8326362ed41f",
        "LOOP_UNROLL_EXCEPTION", "D25", "D26", "D30", "D31", "D32",
    ]
    for anchor in spec_anchors:
        if anchor not in spec:
            errors.append(f"reference spec missing anchor: {anchor}")

    skill_anchors = [
        "Variable-version boundary", "While loop baseline", "same reachable chain's later `Last` branch",
        "DESCENTE_INFINIE_RETEST_GATES.md", "validate_layout_plan",
        "Every source loop format lowers to a structured `While`",
        "Plan While connections before wiring",
        "sbs::function::while", "LOOP_UNROLL_EXCEPTION", "7.9.10", "7.10", "SOP-5B",
        "nodes_per_statement", "cross-band", "L16", "planned coordinate",
        "multiplication node selection table", "mulscalar", "Vector", "atan2",
        "no x/y swap", "numeric-semantics selection table", "SD_BUILTIN_FUNCTIONS",
        "fmod", "round_float1", "native cook", "NATIVE_PROBE_RESULTS",
        "silent 0", "probe_sd_semantics", "COMPATIBILITY_MATRIX_v2.5.0", "RUNTIME_REPROBE_REQUIRED", VERSION_EXPECTED,
    ]
    for anchor in skill_anchors:
        if anchor not in skill:
            errors.append(f"SKILL.md missing anchor: {anchor}")

    while_anchors = [
        "Exit Cond. == True", "变量在迭代之间保留", "branch-private",
        "固定次数、编译期常量次数不默认 unroll", "Pixel Processor",
        "sbs::function::while", "do-while", "continue",
        "标准连接模板（推荐，16.0.3 实测）",
    ]
    for anchor in while_anchors:
        if anchor not in while_ref:
            errors.append(f"While baseline missing anchor: {anchor}")

    # Avoid reintroducing disproven over-generalizations or superseded free-choice rules.
    forbidden = [
        "逐像素固定迭代优先展开",
        "固定次数 raymarch 因而优先选择展开",
        "环外不能按名读环内状态",
        "While 或 Functionized unroll 二选一",
        "再在 While 与 unroll 间做有证据的选择",
        "选择 While 或 Functionized unroll",
        # superseded absolute span / node-count walls (replaced by normalized budgets)
        "图节点数 >=160",
        "节点数 >=240",
        "规划布局 Y 跨度 >3072",
        "X 跨度 >4096",
        "Y>5000 或 X>8000",
        # superseded single-source / wrong atan2 guidance stated as a rule
        "源代码atan(p.x,p.y)需输入p.yx",
        "atan2(a)=atan(a.y,a.x)",
        "原子目录即函数全集",
        "只需查原子节点",
        "原子节点已覆盖全部数值函数",
    ]
    for phrase in forbidden:
        if phrase in spec or phrase in skill:
            errors.append(f"obsolete rule still present: {phrase}")

    # v2 production-safety invariants: prevent regression to the v1 probe hazards.
    probe_src = (ROOT / "scripts" / "probe_sd_semantics.py").read_text(encoding="utf-8")
    safety_required = [
        "PKG = pkg_mgr.newUserPackage()",
        "SAFETY_INVARIANT_001",
        "tempfile.mkdtemp(prefix=PROBE_PREFIX",
        "'resources', 'packages', 'functions.sbs'",
        "if len(hits) != 1",
        "probe_report.json",
    ]
    for anchor in safety_required:
        if anchor not in probe_src:
            errors.append(f"probe safety anchor missing: {anchor}")
    safety_forbidden = [
        r'E:\\SD_AI\\_probe\\out',
        "scratches = [p for p in pkg_mgr.getUserPackages()",
        "PKG = scratches[0]",
        "for f in os.listdir(OUT_DIR):\n        try:\n            os.remove",
    ]
    for phrase in safety_forbidden:
        if phrase in probe_src:
            errors.append(f"unsafe probe pattern present: {phrase}")

    comp = (ROOT / "references" / f"compatibility_matrix_v{VERSION_EXPECTED}.json").read_text(encoding="utf-8")
    for anchor in ('"16.0.3"', '"16.0.5"', '"runtime-reprobe-required"', '"exact_designer_version_required_for_measured_semantics": true'):
        if anchor not in comp:
            errors.append(f"compatibility matrix missing anchor: {anchor}")

    runtime_ref = (ROOT / "references" / f"RUNTIME_SEMANTICS_BASELINE_v{VERSION_EXPECTED}.md").read_text(encoding="utf-8")
    for anchor in ("RS1", "RS2", "RS3", "RS4", "SAFETY_INVARIANT_002", "RS6", "$pos", "$size", "mulscalar(Sequence(float4)"):
        if anchor not in runtime_ref:
            errors.append(f"runtime semantic baseline missing anchor: {anchor}")
    for anchor in ("SAFETY_INVARIANT_002", "Pixel Processor `$pos` is normalized", "Sequence-derived vectors", "RUNTIME_SEMANTICS_BASELINE_v2.5.0.md"):
        if anchor not in skill:
            errors.append(f"SKILL.md missing runtime anchor: {anchor}")

    for anchor in ("coord_pos_x", "coord_size_x", "get_float2"):
        if anchor not in probe_src:
            errors.append(f"coordinate probe anchor missing: {anchor}")

    openai_text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    short_match = re.search(r'(?m)^  short_description: "([^"]+)"$', openai_text)
    prompt_match = re.search(r'(?m)^  default_prompt: "([^"]+)"$', openai_text)
    if not short_match or not 25 <= len(short_match.group(1)) <= 64:
        errors.append("agents/openai.yaml short_description must be 25-64 characters")
    if not prompt_match:
        errors.append("agents/openai.yaml default_prompt must be a one-line quoted string")
    else:
        prompt = prompt_match.group(1)
        if len(prompt) > 240 or "$sd-pixelprocessor-agent" not in prompt:
            errors.append("agents/openai.yaml default_prompt must be short and mention $sd-pixelprocessor-agent")

    # Markdown integrity: every table block must keep a constant column count,
    # and code fences must be balanced. A single stray '|' silently breaks a
    # table (it did once in the mapping table of §7.5.2), so check it here
    # instead of relying on ad-hoc scans.
    for md in sorted(ROOT.rglob("*.md")):
        lines = md.read_text(encoding="utf-8").splitlines()
        rel = md.relative_to(ROOT).as_posix()
        i = 0
        while i < len(lines):
            if lines[i].lstrip().startswith("|"):
                start = i
                block = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    block.append(lines[i])
                    i += 1
                if len(block) >= 2:
                    counts = [row.count("|") for row in block]
                    if len(set(counts)) > 1:
                        first = counts[0]
                        bad = [
                            f"L{start + 1 + k} ({counts[k]} vs {first})"
                            for k in range(len(block))
                            if counts[k] != first
                        ]
                        errors.append(f"{rel}: table starting at L{start + 1} has mixed column counts: {', '.join(bad)}")
            else:
                i += 1
        fences = sum(1 for ln in lines if ln.startswith("```"))
        if fences % 2:
            errors.append(f"{rel}: unbalanced code fences ({fences})")

if errors:
    print("SKILL VALIDATION: FAIL")
    for e in errors:
        print("-", e)
    sys.exit(1)

print("SKILL VALIDATION: PASS")
print("name: sd-pixelprocessor-agent")
print(f"version: {VERSION_EXPECTED}")
print(f"reference: references/{SPEC.name}")
print(f"while baseline: references/{WHILE_REF.name}")
