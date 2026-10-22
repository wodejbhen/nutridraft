# NutriDraft

NutriDraft 是一个**离线营养标签科普工作台原型**：读取本地 JSON，按输入提供的单位归一营养数值，生成结构化报告、简报和待审阅内容草稿。项目使用 Python 3.10+ 标准库，不需要第三方依赖、网络或 API。它是新生成的早期原型，没有长期维护或实际采用记录。

> 本工具仅用于营养信息整理与一般科普草稿，不诊断疾病、不提供处方或个体化治疗建议，也不保证内容符合法律法规、标签规范或平台政策。生成结果须由具备相应知识的人员核对后再使用。

## 快速开始

在项目根目录执行：

```bash
python3 -m nutridraft examples/label_demo.json --output output/demo
```

生成 `output/demo/report.json`、`output/demo/brief.md` 和 `output/demo/content_draft.md`。程序拒绝覆盖已存在的输出目录；再次体验时请将命令末尾改为 `output/my-first-run`。生成的 `output/` 默认不提交到仓库。

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

仅使用 Python 标准库，不需要安装依赖。工具以本地文件为输入和输出，不访问网络、不调用外部 API。

## 输入 JSON

顶层字段如下。数值型字段应为 JSON 数字；`serving_size` 必须为正数，单位仅支持 `g` 或 `ml`。营养项的 `basis_unit` 必须与 `serving_unit` 同属质量或体积维度；不允许在 g 与 ml 之间换算。营养项自身的 `unit` 原样保留，不进行营养单位换算。重复的营养名称应拒绝处理。

```json
{
  "topic": "合成示例：某饮品的营养信息",
  "serving_size": 250,
  "serving_unit": "ml",
  "nutrients": [
    {
      "name": "蛋白质",
      "amount": 3.2,
      "unit": "g",
      "basis_amount": 100,
      "basis_unit": "ml"
    },
    {
      "name": "钠",
      "amount": 40,
      "unit": "mg",
      "basis_amount": 100,
      "basis_unit": "ml"
    }
  ],
  "evidence": [
    {
      "id": "EXAMPLE-1",
      "claim": "示例主张，仅用于演示引用格式。",
      "url": "https://example.invalid/source",
      "title": "虚构示例来源"
    }
  ],
  "draft_text": "合成的待编辑文案。"
}
```

字段含义：

- `topic`：主题字符串。
- `serving_size`、`serving_unit`：每份大小与单位。
- `nutrients`：营养项列表；每项包含 `name`、`amount`、`unit`、`basis_amount`、`basis_unit`。数值表示在 `basis_amount` 指定基准量下的含量。
- `evidence`：来源列表，每项包含 `id`、`claim`、`url`、`title`。输出引用遵循输入信息，不代表来源或主张已被核实。
- `draft_text`：供规则扫描的待编辑文案；保存在 JSON 报告中，不自动改写或写入新口播模板。

归一结果包括每 100 g/ml 及每份的数值，营养项原始 `unit` 保持不变。换算仅按同一 g 或 ml 维度进行，不做密度推断或跨维度转换。请勿据此推断不同单位的营养量可直接比较。

## 输出与生成方式

原型输出 `report.json`、`brief.md`、`content_draft.md`。内容草稿由固定模板对输入文本和数据进行编排，**不是 AI 推理、营养学判断或证据综合**。输入的 evidence 会原样引用或呈现；工具不联网核查 URL、来源真实性、证据质量或 claim 是否成立。请人工确认每条引文、数字、上下文和使用许可。

对极端用语及医疗保证类词语，原型仅作规则提示，要求人工审阅；提示不是完整的风险检测，也不能替代专业、法律或合规审查。没有提示不表示内容安全、真实或合规。

## 安全与使用限制

- 不输入可识别个人的健康资料、病史、检测结果或其他敏感信息；示例数据为纯合成数据，不含真实用户数据。
- 不把结果用作诊断、治疗、处方、疾病预防保证或紧急健康决策。
- 检查本地输入文件和输出目录权限；不要运行来源不明的输入或代码。
- 本项目不访问网络、不要求 API key；若使用者自行改造为联网服务，应另行评估隐私与安全风险。
- 营养标签规定、适用地区和发布平台要求可能不同，须由使用者自行核实。

## 项目状态及文件

项目是首次公开发布的早期原型，不代表已有用户、维护历史或成熟开源项目。已完成本地示例运行及22项自动测试；GitHub Actions 的实际运行状态请查看仓库 Actions 页面。采用 MIT 许可证，版权署名为 wodejbhen。当前文件包括：

- `nutridraft/`：已可运行的命令行原型代码。
- `examples/label_demo.json`：纯合成演示输入。
- `tests/`：原型测试。
- `docs/application-notes.md`：供用户审阅的项目说明与申请相关注意事项。
- `CONTRIBUTING.md`、`SECURITY.md`：贡献和安全说明。
- `LICENSE`：MIT 许可证。
