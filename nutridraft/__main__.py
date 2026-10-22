"""Run with python3 -m nutridraft input.json --output output/demo."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
from .core import analyze, render_brief, render_content


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'JSON键重复：{key}')
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='离线营养标签换算与科普模板（待人工审核）')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, default=Path('output/demo'))
    args = parser.parse_args(argv)
    try:
        if args.input.stat().st_size > 1024 * 1024:
            raise ValueError('输入文件不得超过1MiB')
        data = json.loads(args.input.read_text(encoding='utf-8'), parse_float=Decimal,
                          object_pairs_hook=reject_duplicate_keys)
        report = analyze(data)
        # Do not silently overwrite user work or traverse a pre-existing output directory.
        if args.output.exists():
            raise ValueError('输出目录已存在；请选择新目录，避免覆盖文件')
        args.output.mkdir(parents=True, exist_ok=False)
        artifacts = {'report.json': json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                     'brief.md': render_brief(report), 'content_draft.md': render_content(report)}
        for name, content in artifacts.items():
            with (args.output / name).open('x', encoding='utf-8') as handle:
                handle.write(content)
        print(f'生成3个本地草稿文件：{args.output}；人工审核前不可直接发布。')
        return 0
    except (ValueError, OSError, ArithmeticError, RecursionError) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
