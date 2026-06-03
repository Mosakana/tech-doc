"""
LEGACY (LaTeX path). DEFAULT is now the Markdown skeleton next to this file:
study_guide_skeleton.md → $KNOWLEDGE_VAULT/. Use this .py/.tex path ONLY when
the user explicitly asks for advanced LaTeX typesetting (see SKILL.md "Legacy").

SKELETON for a 学习材料 / 架构详解 (study guide / architecture deep-dive) .tex.

Copy this file to ~/claude-report/<topic>/generate_<topic>.py (every doc
lives in its own per-topic directory — never the claude-report root) and
fill in the placeholder text. Use this when the goal is to teach the
reader a stack or a system, not to recount a debugging journey (use
lessons_learned skeleton for that).

Run:
    mkdir -p ~/claude-report/<topic>
    workon dac && python3 ~/claude-report/<topic>/generate_<topic>.py

Then compile:
    latexmk -lualatex .\<topic>.tex
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # skill root

from latex_template import (
    new_doc, add_title_page, add_toc, add_heading,
    add_para, add_bullet, add_code, add_table, save,
)


def main():
    doc = new_doc()

    # ---- Title page ------------------------------------------------------
    add_title_page(
        doc,
        title='<主题>详解',
        subtitle='<副标题:从"为什么选这套"到"每个模块在做什么">',
        meta_lines=[
            '文档日期:<YYYY 年 M 月 D 日 — use today\'s actual date>',
            '作者:<Your Name>(you@example.com) + Claude Code',
            '适用范围:<谁该看,一句话>',
        ],
    )

    add_toc(doc)

    # ---- 一、背景 ---------------------------------------------------------
    add_heading(doc, '背景:我们到底要解决什么问题', level=1)
    add_para(doc,
        '<2-3 段:这套技术 / 系统是为了解决什么具体问题。把抽象需求落到具体场景。>')

    add_para(doc, '所以选型的核心问题是:**<一句话总结决策核心>**')

    # ---- 二、为什么选 X ---------------------------------------------------
    add_heading(doc, '为什么选 <技术 X>', level=1)

    add_heading(doc, '候选方案对比', level=2)
    add_table(doc, [
        ['方案', '是什么', '为什么没选 / 选它'],
        ['<候选 A>',
         '<一句话描述>',
         '✗ <没选的原因>'],
        ['<候选 B>',
         '<一句话>',
         '✗ <...>'],
        ['<我们选的方案>',
         '<...>',
         '✓ 选它 — <理由>'],
    ])

    add_heading(doc, '选 <X> 的具体理由', level=2)
    add_bullet(doc, '<好处 1,要具体>')
    add_bullet(doc, '<好处 2 — **关键词加粗**>')

    # ---- 三、核心组件 -----------------------------------------------------
    add_heading(doc, '<核心组件 / 三件套 / 主要概念>', level=1)
    add_para(doc,
        '<介绍这一章要讲什么。如果有"几大组件 / 文件夹结构"等,先用 add_code 画出来:>')
    add_code(doc,
        '<目录树 / 模块划分示意图>')

    add_heading(doc, '<组件 A> — <一句话定位>', level=2)
    add_para(doc, '<这个组件做什么>')
    add_code(doc, '<具体的代码 / 配置例子>')
    add_para(doc, '<解释关键概念>')

    add_heading(doc, '<组件 B>', level=2)
    add_para(doc, '<...>')

    # 通常 3-5 个组件,每个一节

    # ---- 四、关键集成机制(可选)------------------------------------------
    add_heading(doc, '<某个集成机制 / 难点 / 跨组件协作>', level=1)
    add_para(doc, '<比如 IAM 授权 + 环境变量传递、JWT 在边缘校验等>')
    add_code(doc, '<具体代码>')
    add_para(doc, '<解释每段在做什么>')

    add_para(doc, '注意几个细节:', bold=True)
    add_bullet(doc, '<细节 1>')
    add_bullet(doc, '<细节 2>')

    # ---- 五、整套链路总览 -------------------------------------------------
    add_heading(doc, '整套链路总览', level=1)
    add_para(doc, '从 <用户起点> 发起一个 <典型操作> 开始,完整链路:')
    add_code(doc,
        '┌────────────┐\n'
        '│  Component │\n'
        '└─────┬──────┘\n'
        '      │\n'
        '      ▼\n'
        '<draw the request flow as ASCII boxes + arrows>')

    # ---- 六、踩过 / 容易踩的坑 --------------------------------------------
    add_heading(doc, '踩过 / 容易踩的坑', level=1)
    add_para(doc, '<列出读者最容易栽跟头的具体行为,每条都要可操作>')
    add_bullet(doc,
        '<具体描述,带"原因 + 怎么避免">',
        bold_prefix='<坑名:>')
    add_bullet(doc,
        '<...>',
        bold_prefix='<坑名:>')

    # ---- 七、参考资源 -----------------------------------------------------
    add_heading(doc, '参考资源', level=1)
    add_bullet(doc, '<官方文档 URL 1>')
    add_bullet(doc, '<官方文档 URL 2>')
    add_bullet(doc, '<本仓库 README + CLAUDE.md(整套架构决策的源头)>')

    save(doc, '<output-dir>/<topic>/<filename>.tex')


if __name__ == '__main__':
    main()
