"""Offline, deterministic label-to-content prototype; not medical advice."""
from decimal import Decimal, InvalidOperation, localcontext
from urllib.parse import urlsplit
import re

DISCLAIMER = '仅供一般科普编辑与人工核对，不构成医疗、诊断或个体膳食建议。未检出风险不代表内容正确或合规。'
RULES = (
    ('medical', r'治愈|根治|包治|降血糖|替代药物|不用吃药', '涉及医疗效果或替代治疗，请删除或交由有资质人员核查。'),
    ('guarantee', r'百分百|100%|绝对安全|零风险|保证瘦|最健康|全网第一', '绝对化或保证性表述需要人工审阅。'),
    ('restriction', r'断食|不吃饭|暴瘦|一周瘦', '涉及极端减重或限制性饮食，需人工审阅。'),
)


def text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 10000:
        raise ValueError(f'{field}: 需要非空字符串（最长10000字符）')
    return value.strip()


def number(value, field, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f'{field}: 需要有限数字')
    try:
        n = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f'{field}: 无效数字') from exc
    if not n.is_finite() or n < 0 or (positive and n == 0) or n > Decimal('1e12'):
        raise ValueError(f'{field}: 数字必须有限、非负且不超过1e12；基准和份量必须大于0')
    return n


def formatted(n):
    with localcontext() as ctx:
        ctx.prec = 60
        return format(n.quantize(Decimal('0.001')), 'f').rstrip('0').rstrip('.') or '0'


def audit(content):
    findings = []
    for code, pattern, message in RULES:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            findings.append({'code': code, 'match': match.group(), 'start': match.start(), 'message': message})
    return findings


def analyze(data):
    if not isinstance(data, dict):
        raise ValueError('根对象必须是JSON对象')
    topic = text(data.get('topic'), 'topic')
    serving = number(data.get('serving_size'), 'serving_size', True)
    base_unit = data.get('serving_unit')
    if base_unit not in ('g', 'ml'):
        raise ValueError('serving_unit: 只接受g或ml，不自动按密度换算')
    nutrients = data.get('nutrients')
    if not isinstance(nutrients, list) or not nutrients or len(nutrients) > 100:
        raise ValueError('nutrients: 需要1至100条营养项')
    rows, seen = [], set()
    with localcontext() as ctx:
        ctx.prec = 60
        for item in nutrients:
            if not isinstance(item, dict):
                raise ValueError('营养项必须是对象')
            name = text(item.get('name'), 'nutrient.name')
            key = name.casefold()
            if key in seen:
                raise ValueError('营养名称不能重复')
            seen.add(key)
            amount = number(item.get('amount'), 'nutrient.amount')
            basis = number(item.get('basis_amount'), 'nutrient.basis_amount', True)
            if item.get('basis_unit') != base_unit:
                raise ValueError('不能混用g与ml；请核对同一食品的计量基准')
            unit = item.get('unit')
            if unit not in ('g', 'mg', 'µg', 'kJ', 'kcal'):
                raise ValueError('营养量单位只接受g/mg/µg/kJ/kcal，不自动换算')
            rows.append({'name': name, 'unit': unit, 'input_amount': str(amount),
                         'input_basis': str(basis), 'basis_unit': base_unit,
                         'per_100': formatted(amount * 100 / basis),
                         'per_serving': formatted(amount * serving / basis)})
    evidence = data.get('evidence', [])
    if not isinstance(evidence, list) or len(evidence) > 100:
        raise ValueError('evidence必须是列表（最多100条）')
    sources, ids = [], set()
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError('证据项必须是对象')
        source = {key: text(item.get(key), 'evidence.' + key) for key in ('id', 'claim', 'url', 'title')}
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', source['id']) or source['id'] in ids:
            raise ValueError('证据id必须唯一，且为1至64位字母数字下划线连字符')
        ids.add(source['id'])
        try:
            url = urlsplit(source['url'])
            valid = url.scheme in ('http', 'https') and bool(url.hostname) and not url.username and not url.password and not any(c.isspace() for c in source['url'])
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('证据URL需要有效HTTP(S)地址，不接受凭据；程序不会请求该地址')
        sources.append(source)
    draft = data.get('draft_text', '')
    if not isinstance(draft, str) or len(draft) > 100000:
        raise ValueError('draft_text必须是字符串，最长100000字符')
    findings = audit(topic + '\n' + draft + '\n' + '\n'.join(s['claim'] for s in sources))
    warnings = ['输入标签数据未经独立核验；换算保留三位小数，并非实验室结果。',
                '规则扫描不理解语境，可能误报或漏报；所有内容必须人工审核。',
                '证据是用户提供的线索：程序未访问网页，也未验证其真实性或是否支持对应说法。']
    if not sources:
        warnings.append('没有证据条目：不得将本草稿视为有来源支持的营养功效说明。')
    return {'project_status': 'new_local_prototype', 'topic': topic,
            'serving_size': str(serving), 'serving_unit': base_unit,
            'nutrients': rows, 'evidence': sources, 'findings': findings,
            'input_draft': draft, 'warnings': warnings, 'publish_ready': False,
            'disclaimer': DISCLAIMER}


def safe_md(value):
    # Render supplied text as text, not active HTML/Markdown links.
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\\', '\\\\').replace('|', '\\|').replace('[', '\\[').replace(']', '\\]').replace('*', '\\*').replace('`', '\\`').replace('\n', ' ')


def render_brief(report):
    unit = report['serving_unit']
    lines = ['# 营养标签编辑简报（待人工审核）', '', safe_md(report['topic']), '',
             f"本次计算份量：{report['serving_size']}{unit}；这不是建议摄入量。", '',
             f'|营养项|每100{unit}|每份|', '|---|---:|---:|']
    for row in report['nutrients']:
        lines.append(f"|{safe_md(row['name'])}|{row['per_100']} {row['unit']}|{row['per_serving']} {row['unit']}|")
    lines += ['', '## 证据线索（未独立验证）']
    for source in report['evidence']:
        lines += [f"- [{source['id']}] {safe_md(source['claim'])}", f"  来源标题：{safe_md(source['title'])}；URL：{safe_md(source['url'])}"]
    if not report['evidence']:
        lines.append('尚未提供来源。')
    lines += ['', '## 文字风险提示']
    for finding in report['findings']:
        lines.append(f"- {safe_md(finding['match'])}：{finding['message']}")
    if not report['findings']:
        lines.append('未匹配预设词条，不代表科学正确或合规。')
    lines += ['', '## 人工核对', '- [ ] 逐字核对原包装标签、份量、单位', '- [ ] 打开每条来源并核对是否确实支持说法', '- [ ] 核查目标地区食品标签与内容传播规则', '- [ ] 删除无法验证的功效、体验、医疗和保证表述']
    lines += ['', *('- ' + w for w in report['warnings']), '', DISCLAIMER, '']
    return '\n'.join(lines)


def render_content(report):
    lines = ['# 科普口播模板（规则生成，不是AI推理）', '', '状态：待人工审阅，不可直接发布。', '',
             '## 开场', '看到营养数字，先问：这是每100克、每100毫升，还是每一份？', '', '## 演示']
    for row in report['nutrients']:
        lines.append(f"本次录入示例中，{safe_md(row['name'])}每100{report['serving_unit']}为{row['per_100']}{row['unit']}；按录入的{report['serving_size']}{report['serving_unit']}一份计算，为{row['per_serving']}{row['unit']}。")
    lines += ['', '## 结尾', '本次只演示按标签基准作算术换算，不据此给食物打健康分，也不推断疾病或减重效果。', '',
              '## 录入的证据线索（仅供编辑核对，不自动写成事实）']
    for source in report['evidence']:
        lines.append(f"- [{source['id']}] {safe_md(source['claim'])}；来源：{safe_md(source['url'])}")
    lines += ['', '## 发布前', '对照 brief.md 完成人工核验。不要将合成演示数据当作真实产品测量值。', '', DISCLAIMER, '']
    return '\n'.join(lines)
