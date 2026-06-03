# Knowledge vault 结构规范

知识库的根是 **`$KNOWLEDGE_VAULT`**(Windows 的 `D:\Knowledge`,WSL 下走 `/mnt/d`)。
它是一个 **Obsidian vault**(根目录有 `.obsidian/`)。所有 tech-doc 产出的知识文档、
以及它们引用的源文档,都落在这里。

这份文件是目录布局的唯一权威。SKILL.md 第 3/6 步会引用它。

---

## 1. 顶层布局

```
$KNOWLEDGE_VAULT/
├── .obsidian/                  ← Obsidian 配置,别动
├── _home.md                   ← vault 首页 / MOC(map of content),手动维护的入口
├── <大方向域>/                 ← 顶层 = 广义主题域(llm/ bota-one/ ops/ ...)
│   ├── <子主题>/               ← 可嵌套:把"同大方向、细分不同"的文档收在一起
│   │   ├── <某篇知识文档>.md   ← 知识笔记,平铺为文件
│   │   ├── <另一篇>.md
│   │   └── attachments/       ← 该子目录下笔记的图片(按需创建)
│   │       └── foo.png
│   └── <另一个子主题>/
└── reference/                 ← 被引用、但不是本库原创的源文档
    ├── reference.md          ← reference 域 MOC + provenance 台账(_home 链它,它链各快照)
    ├── <project>/            ← 按来源项目分组,避免平铺堆积
    │   ├── prd.md
    │   └── spec.md
    └── <another-project>/
```

真实例子(当前库):`llm/ai-ask/` 收 Bota AI Ask 系统的检索/流式/消息分支三篇(同系统、不同侧面),
`llm/compliance-rag/` 收 cosmind 合规 RAG,`llm/chat-product/` 收 chat 产品调研 —— 都在 `llm/` 这个
大方向下,但细分各自独立。

**两类内容,泾渭分明:**

- **知识文档(我们写的)** → 进 `<category>/`。这是库的主体,是"经验沉淀"。
- **参考源文档(别处来的)** → 进 `reference/<project>/`。它们是知识文档**引用的证据**,
  不是我们写的,本质是快照。

---

## 2. 分类怎么定(允许多层嵌套)

知识文档归到一条**目录路径**里,**顶层是广义大方向域,下面可按细分嵌套子目录**。
关键原则:**别用"细技术"当顶层**(那会把同一大方向、只是细分不同的文档拆散)。

> [!important] 历史教训:为什么要嵌套
> 早期顶层用了 `rag/`(一个细技术)。结果 Bota AI Ask 的检索、流式、消息分支三篇——本是
> **同一个系统的不同功能侧面**——要么挤在"rag"下名不副实,要么散到 `rag/`+`product/`。
> 正解:顶层用大方向 `llm/`,下设 `ai-ask/` 把这三篇收一起;`rag` 退化成其中一篇的主题,不再是目录。

**定位一篇文档的步骤:**

1. **先选顶层大方向域**:这篇属于哪个广义领域?(`llm/` LLM/AI 应用、`bota-one/` Bota One app
   工程、`ops/` 运维、`architecture/` 通用架构…)。顶层可以是**技术域**也可以是**项目**——取哪个
   更能把"会持续产出的一簇文档"自然聚起来。
2. **再选/建子主题**:大方向下,这篇和哪些已有文档是"同一系统/同一细分"?有合适子目录就进去
   (`llm/ai-ask/`);没有就在该大方向下新建一个子目录(`llm/chat-product/`)。
3. **每层都"先复用,后新建"**:`ls` 看现有路径,能塞进现有目录就别新开近义的
   (别同时有 `llm/ai-ask/` 和 `llm/ai-chat/`)。
4. **层数按需,不强求深度**:大多数 2 层就够(`大方向/子主题/文件.md`);某个大方向下文档还少时,
   直接平铺在大方向里也行(如 `ops/` 暂时平铺 3 篇),等长大了再开子目录。别为了嵌套而嵌套。
5. **目录名**:英文 kebab-case、短(`ai-ask`、`chat-product`、`compliance-rag`),好打好 `#tag` 化。

**当前结构(随库演进,以实际 `ls` 为准):**

| 路径 | 收什么 |
|---|---|
| `llm/ai-ask/` | Bota AI Ask 系统的各功能侧面(检索/RAG、流式、消息分支…) |
| `llm/chat-product/` | LLM chat 的产品 / 体验 / 竞品调研 |
| `llm/compliance-rag/` | 合规场景的 RAG(cosmind) |
| `bota-one/` | Bota One app 工程(后端、重构、构建踩坑…) |
| `ops/` | 运维 / DevOps / OpenClaw(Larry、运维调研、跨账号认证…) |
| `architecture/` | 通用软件架构模式 / 选型 / 部署拓扑 |

新建顶层或子目录时,顺手在 `_home.md` 的分类表里加一行,让首页能导航到它。

### 域索引(MOC)— 让层级在 graph 上显形

Obsidian 的 graph **只认链接、不认文件夹**,所以光有嵌套目录,图谱上看不出层级。
解决:每个域(含子域)有一个**索引笔记**(folder-note,文件名 = 文件夹名,如 `llm/llm.md`、
`llm/ai-ask/ai-ask.md`),它链 DOWN 到本域文档 + 子域索引,链 UP 到父域索引(顶层域上链 `_home`)。
于是图谱出现一棵树:`_home → llm → ai-ask → {三篇文档}`,而文档间真实的 `related` 横向链照旧 ——
**层级 + 关系两者都在图上**。

- **不要手写/手改索引**:它们由 `${CLAUDE_SKILL_DIR}/scripts/build_indexes.py` 从目录结构**自动生成**
  (幂等、带 `type: moc`、带"AUTO-GENERATED"标记)。
- **每次加 / 移 / 删知识文档后**,重跑一次让索引跟上:
  ```bash
  $SKILL_PYTHON ${CLAUDE_SKILL_DIR}/scripts/build_indexes.py
  ```
- `_home.md` 是**手动**维护的根 MOC(脚本不碰它),链到各顶层域索引(`[[llm]]`/`[[bota-one]]`/…)。
- 索引文件名 = 文件夹名 → basename 唯一,`[[llm]]`/`[[ai-ask]]` 直接解析(别让两个文件夹重名)。

---

## 3. 知识文档文件本身

- **平铺为 `.md` 文件**,不是每篇一个子目录。文件名用**中文主题名**
  (`合规审查与LLM-RAG结合的系统设计.md`),体现内容,不带 `v1`/`final` 版本后缀
  (版本交给 git / 文件历史)。
- **图片**进**和笔记同一个(叶子)目录下的 `attachments/`**,笔记里用相对路径
  `![[attachments/foo.png]]`(Obsidian 嵌入语法)或标准 `![](attachments/foo.png)`。
  移动笔记到别的目录时,记得把它的 `attachments/` 一起搬(相对路径才不断)。
- **PDF 导出件**(如果生成了)放在**同目录同名** `.pdf`,跟 `.md` 并排。PDF 是产物,
  gitignore 掉(见 § 6)。

---

## 4. reference/ —— 源文档怎么放,怎么不堆积

**这是用户明确担心"越积越多"的地方,纪律如下:**

1. **按来源项目分组**:`reference/<project>/<doc>.md`,例如
   `reference/cosmind/prd.md`、`reference/bota/ai-ask-retrieval-design.md`。
   **永远不要**把源文档平铺在 `reference/` 根下 —— 那正是会堆乱的结构。
2. **快照,不是镜像**:reference 里的文件是**写知识文档当时**引用的那个版本的快照。
   不追求跟源文件实时同步(那是 git submodule 的活,不是知识库的活)。
   知识库要的恰恰是"我当时引用的是哪个版本"。
3. **每个快照带 provenance frontmatter**,记清楚它从哪来、什么时候拍的:

   ```yaml
   ---
   title: Cosmind 技术 PRD
   type: reference
   source_project: cosmind
   source_path: /abs/path/to/cosmind/docs/product/prd.md
   source_sha256: 002f29891f98...   # 源文件内容哈希,用于低成本检测改动(见「更新协议」)
   snapshot_date: 2026-06-02
   snapshot_reason: 被《合规审查与LLM-RAG结合》§4/§8 引用
   aliases: [prd]
   tags: [reference, cosmind, prd]
   ---
   ```

4. **维护 `reference/reference.md`**:它既是防堆积"账本"(每个快照一行,记 `[[wikilink]]`、来源项目、
   快照日期、为什么收它——一眼看出哪些还在被引用、哪些没人链接可清理),又是 **reference 域的 MOC**
   (`_home` 只链它、不散链单篇;它 `type: moc`、带 `> 上级:[[_home]]`,使 reference 也进层级树)。
   它**手动维护**(provenance 信息脚本生成不了),`build_indexes.py` 跳过整个 `reference/`。
5. **去重**:复制前先看 `reference/<project>/` 下有没有同名/同源的旧快照。
   有就**更新那一份**(覆盖 + 更新 `snapshot_date`),不要拍第二张。
6. **命名 = 知识文档引用它时用的稳定 slug**(如 `bota-rag-ai-ask.md`、`cosmind-spec.md`),
   **不要**为了"保留原名"而用 `spec.md` 然后指望 alias 兜底 —— **Obsidian 的 alias 链接解析不可靠**
   (实测 `[[cosmind-spec]]` 指向 `spec.md`+alias 会空解析;文件名直接叫 `cosmind-spec.md` 才稳)。
   原始文件名 / 路径记进 frontmatter 的 `source_path`(也可加进 `aliases` 备查)。
   slug 用短横线 kebab-case,不加项目前缀(项目信息已由 `<project>/` 文件夹表达)。
7. **修内部交叉引用**:源文档里常带指向同仓库其它文档的相对链接(如 PRD 里
   `[docs/spec.md](spec.md)`)。复制进 vault 后这些相对路径会断成"空引用"。处理:
   - 目标**已在我们 reference 里** → 改成本地 `[[slug]]`(保留原显示文字:`[[cosmind-spec|docs/spec.md]]`)。
     这样既消空引用,又能在 graph 里把 reference 之间连起来。
   - 目标**没被快照** → 退化成纯文字(去掉链接语法),别留断链。
   - **外部 `https://` URL 原样保留**(它们正常解析,不是空引用)。
   复制后用一次链接扫描确认 0 断链(wikilink + 相对 md 链接都查)。

### 更新协议:源文档改了怎么低成本刷新快照

源文档(尤其 PRD/spec)会持续改。**核心思路:把源文件的 sha256 存进快照 frontmatter
(`source_sha256`),检查改动时在 shell 里重算哈希比对——未改动的文件 agent 一个字都不用读
(零 token)。** reference 再多、只要改动的少,检查成本就极低。两个脚本在
`${CLAUDE_SKILL_DIR}/scripts/`:

- **`check_references.sh`** — 扫 `reference/**`,逐个把源文件当前 sha 和快照存的 `source_sha256`
  比对,只打印 `CHANGED` / `MISSING-SRC` / `NO-HASH`(未改动的只计数、不逐条列)。纯 shell。
- **`refresh_reference.sh <snapshot.md>`** — 从快照的 `source_path` 重新取正文,**保留我们策划的
  frontmatter**(title/reason/aliases/tags…),只更新 `snapshot_date` + `source_sha256`,正文换成最新源。
  机械操作,~0 token。

**一句话触发(agent 行为):**

| 用户说 | agent 做 |
|---|---|
| "检查 reference 有没有更新" / "刷新 reference" | 跑 `check_references.sh` → 对每个 `CHANGED`/`NO-HASH` 跑 `refresh_reference.sh` → 跑链接扫描 → 报告改了哪几篇 |
| "prd 改了,更新快照" / "更新 <名> 快照" | 直接 `refresh_reference.sh reference/<proj>/<名>.md` → 链接扫描 → 报告 |
| 新文档第一次收进来 | 走上面 1–7 的初次快照流程(含写 `source_sha256`) |

**token 成本**:检查 = 纯 shell(零);刷新 = 纯 shell(零);唯一可能花 token 的是——若某篇改动后的
新正文带了指向 vault 内文档的相对链接,要按 rule 7 改成 `[[slug]]`,但**只发生在真正改了的那几篇**。
所以「100 篇 reference、这周只改了 1 篇」≈ 只有那 1 篇进 agent 上下文。

> [!note] 为什么用哈希而非 mtime
> `git pull` / 编辑器保存常会动 mtime 但内容没变;哈希只在**内容真变**时报 CHANGED,避免无谓刷新。

### 什么算 reference,什么不算

- ✅ 是 reference:别的项目仓库里的 PRD、spec、设计文档、调研笔记,被某篇知识文档引用。
- ❌ 不是 reference:公开网页 / 论文 / 官方文档 —— 这些在知识文档正文里用 URL 链接就行,
  不必拉进库(它们不是"我的"资产,且会无限膨胀)。reference 只收**私有的、仓库内的、
  会被反复回看的**源文档。

---

## 5. 链接与标签(让它成为"图"而不是"一摞文档")

- **双链优先**:知识文档之间、知识文档→reference,用 `[[文件名]]` 或 `[[文件名|显示文字]]`。
  Obsidian 按笔记名解析,跨 category 也能链。
- **frontmatter `tags`**:每篇至少 2-3 个 tag,跟 category 呼应 + 细分主题
  (`[rag, citation, 踩坑]`)。标签视图是除双链外的第二种检索面。
- **frontmatter `related`**:列出强相关的几篇,帮 graph view 连边。
- **指向尚不存在的笔记的 `[[ ]]` 是允许的**——它标记"这篇值得以后写",不是错误。

---

## 6. git / 忽略

如果 vault 纳入 git(推荐),`.gitignore` 至少包含:

```
.obsidian/workspace*       # Obsidian 的本地 UI 状态,不该进版本库
*.pdf                      # PDF 是 md 的产物,按需重渲,不入库
.DS_Store
```

`.md`(知识文档 + reference 快照 + 各域 MOC 索引)、`attachments/` 里的图、`_home.md` 都**入库**。
