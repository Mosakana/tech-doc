"""
LEGACY (LaTeX path). DEFAULT is now the Markdown skeleton next to this file:
lessons_learned_skeleton.md → $KNOWLEDGE_VAULT/. Use this .py/.tex path ONLY when
the user explicitly asks for advanced LaTeX typesetting (see SKILL.md "Legacy").

SKELETON for a 踩坑记 (lessons-learned) .tex.

Copy this file to ~/claude-report/<topic>/generate_<topic>.py (every doc
lives in its own per-topic directory — never the claude-report root) and
fill in the placeholder text. The shape of the document is fixed; only
the content varies per debugging episode.

Run:
    mkdir -p ~/claude-report/<topic>
    workon dac && python3 ~/claude-report/<topic>/generate_<topic>.py

Then compile (where lualatex is available — TeX Live on the user's Windows side):
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
        title='<项目名> <场景>踩坑记',
        subtitle='<一句副标题:具体踩了什么坑、最后怎么解的>',
        meta_lines=[
            '文档日期:<YYYY 年 M 月 D 日 — use today\'s actual date>',
            '作者:<Your Name>(you@example.com) + Claude Code',
            '适用范围:<谁该看这个文档,一句话>',
        ],
    )

    add_toc(doc)

    # ---- 一、背景 ---------------------------------------------------------
    add_heading(doc, '背景:这次到底在干什么', level=1)
    add_para(doc, '<2-3 句话:我们在做什么、原本期望什么。>')
    add_bullet(doc, '<决策 1>')
    add_bullet(doc, '<决策 2>')

    add_heading(doc, '这份文档想达到的目的', level=2)
    add_bullet(doc, '把每个错误的来龙去脉讲清楚,以后再看到类似报错知道是什么意思。')
    add_bullet(doc, '把过程中涉及到的技术名词从零讲一遍。')
    add_bullet(doc, '总结整件事的根因 + 关键教训。')

    # ---- 二、技术名词速查 -------------------------------------------------
    add_heading(doc, '技术名词速查(看后面问题之前先看这里)', level=1)
    add_para(doc,
        '后面讲问题的时候会反复提到下面这些词。建议先把这一章看完,'
        '后面看错误链路会清楚很多。')

    add_heading(doc, '<概念 1 — 比如 hoisting>', level=2)
    add_para(doc, '<从零开始解释,假设读者完全不懂>')
    add_code(doc, '<代码 / 命令示例>')

    add_heading(doc, '<概念 2>', level=2)
    add_para(doc, '<...>')

    # 一般 6-10 个概念,每个一节

    # ---- 三、问题链路(按时间顺序)----------------------------------------
    add_heading(doc, '问题链路(按时间顺序)', level=1)
    add_para(doc,
        '下面是按真实发生顺序梳理的。每一步都包括:'
        '出现什么报错、当时怎么想、做了什么、为什么对 / 为什么没用。')

    add_heading(doc, '起点:<最初的报错>', level=2)
    add_para(doc, '操作:<用户做了什么操作触发的>')
    add_para(doc, '报错(节选):')
    add_code(doc, '<完整 / 节选的报错文本>')
    add_para(doc, '当时的判断:', bold=True)
    add_bullet(doc, '<猜测 1>')
    add_bullet(doc, '<猜测 2>')
    add_para(doc, '第一次尝试的修复:', bold=True)
    add_para(doc, '<尝试了什么>')
    add_para(doc, '结果:<为什么没解决问题>')

    add_heading(doc, '第一个错误的修复:<尝试名>', level=2)
    add_para(doc, '判断(错误):', bold=True)
    add_bullet(doc, '"<当时的错误猜测,加引号>"')
    add_para(doc, '操作:')
    add_code(doc, '<具体改了什么>')
    add_para(doc, '为什么这是个错误的修复:', bold=True)
    add_bullet(doc, '<原因 1 — 用 **inline 加粗** 强调关键词>')
    add_bullet(doc, '<原因 2>')

    # ... 继续按真实时间线展开 3.3、3.4 ...

    add_heading(doc, '关键转折:<事件,如"去看 demo 仓本身怎么装的">', level=2)
    add_para(doc,
        '<这一节描述发现真根因的那个时刻 — 通常是退一步、看参考实现、查文档、'
        '问别人。这是整个故事的高潮。>',
        italic=True)

    add_heading(doc, '真正的根因 + 真正的修复', level=2)
    add_para(doc, '根因:', bold=True)
    add_bullet(doc, '<一句话总结根因>')
    add_para(doc, '修复:', bold=True)
    add_bullet(doc, '<具体改动 1>')
    add_bullet(doc, '<具体改动 2>')

    # ---- 四、修复尝试汇总表 -----------------------------------------------
    add_heading(doc, '所有修复尝试汇总(一张表看完)', level=1)
    add_table(doc, [
        ['尝试', '我们当时的猜测', '为什么没用 / 为什么对'],
        ['<尝试 1 描述>',
         '<当时的假设>',
         '<事后的判断>'],
        ['<尝试 2 描述>',
         '<...>',
         '<...>'],
        ['<最终生效的修复>',
         '——',
         '<为什么这个对了>'],
    ])

    # ---- 五、教训 ---------------------------------------------------------
    add_heading(doc, '教训', level=1)

    add_heading(doc, '元教训(关于过程的教训)', level=2)
    add_bullet(doc,
        '<比如:"当你需要连续 3 个以上 hack 才能跑通时,该停下来调研工具选型"。'
        '一句话总结 + 引出原因。>',
        bold_prefix='第一条:')
    add_bullet(doc, '<...>', bold_prefix='第二条:')

    add_heading(doc, '对未来类似工作的教训', level=2)
    add_bullet(doc, '<具体建议 1>')
    add_bullet(doc, '<具体建议 2>')

    add_heading(doc, '通用领域知识(给后人看的)', level=2)
    add_bullet(doc, '<跟这次踩坑相关的、值得记住的领域规律 1>')
    add_bullet(doc, '<...>')

    # ---- 六、最终落地的配置 -----------------------------------------------
    add_heading(doc, '最终落地的配置(下次再做这件事直接抄)', level=1)
    add_para(doc, '所有 hack 都已删掉。下面是最终能跑通的最小配置。')

    add_heading(doc, '<文件 1,如 root package.json>', level=2)
    add_code(doc, '<最终的内容片段>')
    add_bullet(doc, '<注意点 1>')
    add_bullet(doc, '<注意点 2>')

    # ---- 七、一句话总结 ---------------------------------------------------
    add_heading(doc, '一句话总结', level=1)
    add_para(doc,
        '<整篇文档浓缩成 1-2 句话,放在最后。如果读者只看一段,就看这一段。>',
        bold=True)

    save(doc, '<output-dir>/<topic>/<filename>.tex')


if __name__ == '__main__':
    main()
