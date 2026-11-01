# EchoLoom 文献搜索地图 v0.1

检索日期：2026-10-31。范围：多来源虚构人物重建、人格表示、原文证据、角色模拟、用户审核。

## 本轮结果与阅读边界

本轮建立 **39 篇候选文献**：保留先前讨论的 5 篇，新增 34 篇。标题、作者和研究问题以论文原文、ACL Anthology、作者主页或项目页为依据。多数条目完成摘要筛选；部分原文用于核对方法、局限和参考文献，**不等于 39 篇均已精读或复现**。下表中的“对我们的启发”和“需要验证”是针对 EchoLoom 的分析，不是论文作者的结论。

优先级：A = 当前 Schema 或 coffee chat 优先；B = 第二轮方法与评估；C = 产品、历史背景或后续扩展。按相关性保留经典研究，不将新近预印本自动视为更可靠。没有使用未经核实的被引次数排名。

## 1. 用户指定的研究者与合作者

[Zixin (Nicole) Zhao](https://zixin.ca/) 的主页标注为多伦多大学计算机科学博士生，研究 HCI、NLP 和可视化；共同导师为 Fanny Chevalier 与 Gerald Penn。她的工作与叙事理解、人物模拟和创作者控制有交集，不能据此认定她专门研究心理学人格测量。

| 合作线索 | 已核实的共同论文 | 对 EchoLoom 的价值 |
| --- | --- | --- |
| Tian Yu、Ken Shi、Gerald Penn ↔ Zixin Zhao | P27 人物模拟 | 角色目标、记忆、状态、故事时间和信息边界 |
| Damien Masson、Fanny Chevalier ↔ Zixin Zhao | P28、P29 | 人物关系／事件的可视化、审核与修改，以及写作者需求 |
| Young-Ho Kim、Gerald Penn ↔ Zixin Zhao | P29 | 用户需求与工具设计的对应关系 |
| Dashiel Carrera、Ashish Ajin Thomas、Daniel Wigdor ↔ Zixin Zhao | P30 | 文本片段组织、由用户主导的迭代 |
| Patrick Yung Kang Lee、Jessica Y. Bo、Anastasia Kuzminykh、Carolina Nobre、Fanny Chevalier 等 ↔ Zixin Zhao | P31 | AI 陪伴关系中的行为稳定性、平台变化和迁移需求 |

以上均为共同作者关系；不推断谁是学生、导师或当前所属实验室成员。

## 2. 文献矩阵

### 2.1 先前的 5 篇起点

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P01 / B | [RoleLLM: Benchmarking, Eliciting, and Enhancing Role-Playing Abilities of Large Language Models](https://aclanthology.org/2024.findings-acl.878/)，Wang 等 | Findings ACL 2024 | 区分角色知识和语言风格；构建扮演基线 | 主要研究角色扮演，不直接解决多来源证据冲突 |
| P02 / A | [FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation](https://aclanthology.org/2023.emnlp-main.741/)，Sewon Min 等 | EMNLP 2023 | 把人物描述拆为可独立验证的原子主张 | 事实精确率不能衡量人格推断是否合理，也不衡量所有遗漏 |
| P03 / B | [An Introduction to the Five-Factor Model and Its Applications](https://pubmed.ncbi.nlm.nih.gov/1635039/)，Robert R. McCrae、Oliver P. John | Journal of Personality 1992 | 稳定特质的理论参照 | 小说材料不是标准问卷；不据此生成伪精确分数 |
| P04 / B | [Personalizing Dialogue Agents: I have a dog, do you have pets too?](https://aclanthology.org/P18-1205/)，Saizheng Zhang 等 | ACL 2018 | PersonaChat：档案信息如何约束对话 | 简短自述档案与复杂虚构人物人格仍有距离 |
| P05 / B | [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)，Joon Sung Park 等 | UIST 2023 | 经历、反思、检索分层 | 可信行为模拟不等于从给定材料准确恢复人物 |

### 2.2 人物理解与人格抽取

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P06 / A | [CHIRON: Rich Character Representations in Long-Form Narratives](https://aclanthology.org/2024.findings-emnlp.499/)，Alexander Gurung、Mirella Lapata | Findings EMNLP 2024 | 问答式人物档案，加独立验证模块过滤错误主张 | 我们仍需补充跨文档优先级和冲突记录 |
| P07 / A | [BookWorm: A Dataset for Character Description and Analysis](https://aclanthology.org/2024.findings-emnlp.258/)，Argyrios Papoudakis、Mirella Lapata、Frank Keller | Findings EMNLP 2024 | 区分事实性 description 与解释性 analysis；按人物检索 | 整本书任务不能直接代表用户混合来源材料 |
| P08 / A | [Personality Understanding of Fictional Characters during Book Reading](https://arxiv.org/abs/2305.10156)，Mo Yu、Jiangnan Li、Shunyu Yao 等 | ACL 2023，PersoNet | 保留情境和长程信息，研究细粒度人格判断 | 特质预测任务不等于完整、可编辑的人格档案 |
| P09 / A | [“Let Your Characters Tell Their Story”: A Dataset for Character-Centric Narrative Understanding](https://arxiv.org/abs/2109.05438)，Faeze Brahman、Meng Huang、Oyvind Tafjord、Chao Zhao、Mrinmaya Sachan、Snigdha Chaturvedi | Findings EMNLP 2021，LiSCU | 人物识别与人物描述任务；检查哪些信息定义一个人物 | 从摘要提取与从全部原始资料重建难度不同 |
| P10 / C | [Learning Latent Personas of Film Characters](https://aclanthology.org/P13-1035/)，David Bamman、Brendan O’Connor、Noah A. Smith | ACL 2013 | 从人物的行动、承受的行动与属性建模 | 潜在角色类型不能直接当作个体心理人格 |
| P11 / B | [Modeling Protagonist Emotions for Emotion-Aware Storytelling](https://aclanthology.org/2020.emnlp-main.426/)，Faeze Brahman、Snigdha Chaturvedi | EMNLP 2020 | 明确情绪轨迹与稳定特质的区别 | 研究目标为生成；不是人格抽取准确率证据 |
| P12 / B | [Feuding Families and Former Friends: Unsupervised Learning for Dynamic Fictional Relationships](https://aclanthology.org/N16-1180/)，Mohit Iyyer、Anupam Guha、Snigdha Chaturvedi、Jordan Boyd-Graber、Hal Daumé III | NAACL 2016 | 人物关系应随事件变化，而不是一个固定标签 | 动态关系表示仍需与人格、来源和时间分开 |
| P24 / B | [BOOKCOREF: Coreference Resolution at Book Scale](https://aclanthology.org/2025.acl-long.1197/)，Giuliano Martinelli、Tommaso Bonomo、Pere-Lluís Huguet Cabot、Roberto Navigli | ACL 2025 | 名字、别名、代词的统一归属与长距离指代 | 整本书共指不直接解决跨版本／跨作品人物同名 |

### 2.3 原文证据、归因与事实校验

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P13 / A | [Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627)，Tianyu Gao、Howard Yen、Jiatong Yu、Danqi Chen | EMNLP 2023，ALCE | 既检查有没有引用，也检查引用是否支持主张 | 问答归因评估不等于人格解释有效性 |
| P14 / B | [ALiiCE: Evaluating Positional Fine-grained Citation Generation](https://aclanthology.org/2025.naacl-long.23/)，Yilong Xu 等 | NAACL 2025 | 细粒度主张与引用位置，避免整段一个来源 | 标注／评估复杂度是否值得，需要小样本实验 |
| P15 / A | [FABLES: Evaluating Faithfulness and Content Selection in Book-length Summarization](https://arxiv.org/abs/2404.01261)，Yekyung Kim、Yapei Chang、Marzena Karpinska、Aparna Garimella、Varun Manjunatha、Kyle Lo、Tanya Goyal、Mohit Iyyer | COLM 2024 | 对人物状态和事件错误、内容遗漏做人工核查 | 该任务中自动评分局限明显；不能只依赖模型给自己评分 |

### 2.4 角色模拟与一致性评估

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P16 / B | [Dialogue Natural Language Inference](https://aclanthology.org/P19-1363/)，Sean Welleck、Jason Weston、Arthur Szlam、Kyunghyun Cho | ACL 2019 | 支持、矛盾、中立的关系类型 | 表面矛盾可能来自不同时间／世界观；先记录上下文 |
| P17 / B | [Will I Sound Like Me? Improving Persona Consistency in Dialogues through Pragmatic Self-Consciousness](https://aclanthology.org/2020.emnlp-main.65/)，Hyunwoo Kim、Byeongchang Kim、Gunhee Kim | EMNLP 2020 | 对话生成时主动考虑 persona 冲突 | 对话端方法，不能替代上游档案质量控制 |
| P18 / B | [PersonaLLM: Investigating the Ability of Large Language Models to Express Personality Traits](https://arxiv.org/abs/2305.02547)，Hang Jiang、Xiajie Zhang、Xubo Cao、Cynthia Breazeal、Deb Roy、Jad Kabbara | Findings NAACL 2024；预印本 2023 | 检查给定特质能否在语言中被表达 | 给定人格后表达成功，不等于从故事推断人格成功 |
| P19 / A | [InCharacter: Evaluating Personality Fidelity in Role-Playing Agents through Psychological Interviews](https://aclanthology.org/2024.acl-long.102/)，Xintao Wang 等 | ACL 2024 | 将访谈式人格评估作为一个验证视角 | 不宜把模型访谈分数作为唯一真实标签 |
| P20 / B | [CoSER: A Comprehensive Literary Dataset and Framework for Training and Evaluating LLM Role-Playing and Persona Simulation](https://arxiv.org/abs/2502.09082)，Xintao Wang 等 | 初稿 2025，当前 v3 为 2026；早期题名为 Coordinating LLM-Based Persona Simulation of Established Roles | 情境、对话、角色经历的联合表示与下游评测 | 标题／版本需固定；训练与评估设置不可混用 |
| P21 / A | [PersonaEval: Are LLM Evaluators Human Enough to Judge Role-Play?](https://arxiv.org/abs/2508.10014)，Lingfeng Zhou、Jialing Zhang、Jin Gao、Mohan Jiang、Dequan Wang | arXiv 2025 | 验证评分器是否能分辨人物、言语和行为归属 | 单一评分模型的高分不能直接代表人类判断 |
| P22 / A | [Rethinking Role-Playing Evaluation: Anonymous Benchmarking and a Systematic Study of Personality Effects](https://arxiv.org/abs/2603.03915)，Ji-Lun Peng、Yun-Nung Chen | arXiv 2026 | 匿名角色测试，控制预训练中已知角色姓名的影响 | 新近论文，仍需细读数据拆分与基线设置 |
| P23 / B | [PICon: A Multi-Turn Interrogation Framework for Evaluating Persona Agent Consistency](https://arxiv.org/abs/2603.25620)，Minseo Kim 等 | arXiv 2026 | 多轮追问与重测，不只看单轮表现 | 真人替身评估需调整为虚构人物的故事世界事实 |

### 2.5 人格理论补充

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P25 / A | [A Cognitive-Affective System Theory of Personality: Reconceptualizing Situations, Dispositions, Dynamics, and Invariance in Personality Structure](https://pubmed.ncbi.nlm.nih.gov/7740090/)，Walter Mischel、Yuichi Shoda | Psychological Review 1995 | 用“若情境 A，则行为 X”的模式描述人格 | 理论迁移到虚构人物是我们的设计假设，需实验 |
| P26 / B | [A New Big Five: Fundamental Principles for an Integrative Science of Personality](https://pubmed.ncbi.nlm.nih.gov/16594837/)，Dan P. McAdams、Jennifer L. Pals | American Psychologist 2006 | 区分稳定特质、适应性目标与个人生命叙事 | 这里的 New Big Five 是整合框架，不是另外五个人格分数 |

### 2.6 Zixin Zhao 本人的相关论文

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P27 / A | [Multi-Agent Based Character Simulation for Story Writing](https://aclanthology.org/2025.in2writing-1.9/)，Tian Yu、Ken Shi、Zixin Zhao、Gerald Penn | In2Writing 2025 | 角色目标、状态、记忆；区分事件发生顺序与叙述顺序 | 是故事生成研究；不能声称已经解决证据型人格重建 |
| P28 / A | [Visual Story-Writing: Writing by Manipulating Visual Representations of Stories](https://zixin.ca/data/pdf/visualstorywriting.pdf)，Damien Masson、Zixin Zhao、Fanny Chevalier | UIST 2025 | 用人物互动、位置、事件时间线支持用户检查和编辑 | 核心为写作交互；人格推断模块仍需另外验证 |
| P29 / A | [Making the Write Connections: Linking Writing Support Tools with Writer’s Needs](https://arxiv.org/abs/2502.13320)，Zixin Zhao、Damien Masson、Young-Ho Kim、Gerald Penn、Fanny Chevalier | CHI 2025 | 用需求研究和文献地图定位我们的工具；补充阅读池入口 | 写作者需求不直接代表所有角色陪伴用户 |
| P30 / B | [Nabokov’s Cards: An AI Assisted Prewriting System to Support Bottom-Up Creative Writing](https://zixin.ca/data/pdf/Nabakov_s_Cards_C_C_2025.pdf)，Dashiel Carrera、Zixin Zhao、Ashish Ajin Thomas、Daniel Wigdor | C&C 2025 | 以片段卡片组织材料，让用户逐步建立解释 | 生成新材料与忠实抽取旧材料须在产品中区分 |
| P31 / B | [Large Language Lovers: Lived Experiences of Negotiating Agency and Platform Control in AI Companionship](https://arxiv.org/abs/2601.13188)，Patrick Yung Kang Lee、Jessica Y. Bo、Zixin Zhao 等 | 2026；作者主页列为 FAccT 2026 | 用户如何维护关系、处理模型变化与跨平台迁移 | 用户研究可指引产品，不提供人格抽取算法 |

### 2.7 沿引用链扩展的叙事与创作工具

| ID / 优先级 | 论文与作者 | 年份／出处 | 对我们的启发 | 需要验证或注意的边界 |
| --- | --- | --- | --- | --- |
| P32 / B | [Character-LLM: A Trainable Agent for Role-Playing](https://aclanthology.org/2023.emnlp-main.814/)，Yunfan Shao、Linyang Li、Junqi Dai、Xipeng Qiu | EMNLP 2023 | 经历如何影响角色表现，可作下游比较 | 合成经历不能倒灌为原著事实；不构成现在微调的理由 |
| P33 / B | [Agents’ Room: Narrative Generation through Multi-step Collaboration](https://arxiv.org/abs/2410.02603)，Fantine Huot、Reinald Kim Amplayo、Jennimaria Palomaki、Alice Shoshana Jakobovits、Elizabeth Clark、Mirella Lapata | ICLR 2025；初稿 2024 | 把人物计划、叙事计划与生成任务拆开 | 写作代理与故事中的人物代理是不同概念 |
| P34 / B | [IBSEN: Director-Actor Agent Collaboration for Controllable and Interactive Drama Script Generation](https://aclanthology.org/2024.acl-long.88/)，Senyu Han、Lu Chen、Li-Min Lin、Zhengshan Xu、Kai Yu | ACL 2024 | 作者控制与角色自身目标如何协调 | 剧情推进可能掩盖人格偏移，需分开评估 |
| P35 / B | [Narrative Planning: Balancing Plot and Character](https://faculty.cc.gatech.edu/~riedl/pubs/jair.pdf)，Mark O. Riedl、R. Michael Young | JAIR 2010 | 人物行为应有可解释的意图与因果关系 | 经典符号规划方法，不直接等价于 LLM 人格模型 |
| P36 / C | [TaleBrush: Sketching Stories with Generative Pretrained Language Models](https://cond.org/talebrush.html)，John Joon Young Chung 等 | CHI 2022 | 用户用轨迹控制角色境遇；启发时间性编辑 | 境遇／命运轨迹不等于人格特质轨迹 |
| P37 / B | [DramatVis Personae: Visual Text Analytics for Identifying Social Biases in Creative Writing](https://www.cs.au.dk/~elm/pdf/dvp.pdf)，Md Naimul Hoque、Bhavya Ghai、Niklas Elmqvist | DIS 2022 | 别名合并、人物提及、形容词与行为的可视检查 | 关注偏差与呈现，不是完整人格提取模型 |
| P38 / C | [Co-Writing Screenplays and Theatre Scripts with Language Models: An Evaluation by Industry Professionals](https://arxiv.org/abs/2209.14958)，Piotr Mirowski、Kory W. Mathewson、Jaylen Pittman、Richard Evans | CHI 2023；初稿 2022，Dramatron | 分层写作与专业创作者反馈 | 从大纲生成剧本不能验证对输入人物的忠实程度 |
| P39 / B | [Narrative Keyframing for Generative Creative Writing](https://arxiv.org/abs/2608.10337)，Chao Zhang、Abe Davis | 2026 预印本；项目页列 UIST 2026 | 人物状态与视角在指定时刻的约束，可启发 profile 版本化 | 属主题扩展，不是 Zixin Zhao 的共同作者论文；不以社交帖子推断作者 |

## 3. 已核实的引用关系

箭头表示“左边论文引用右边论文”，不是影响强度或相互背书。以下在原文正文或参考文献中查到；不宣称是完整引用网络，也没有将单向引用写成双向引用。

| 引用方 → 被引用方 | 核对位置与证据 |
| --- | --- |
| P27 → P05 Generative Agents | [P27 原文](https://zixin.ca/data/pdf/In2Writing2025_Multi_Agent_Based_Character.pdf)，References 中 Park 等 2023 |
| P27 → P32 Character-LLM | 同上，References 中 Shao 等 2023 |
| P27 → P33 Agents’ Room | 同上，相关工作、实验基线与 References 中 Huot 等 2024 |
| P27 → P34 IBSEN | 同上，相关工作与 References 中 Han 等 2024 |
| P27 → P35 Narrative Planning | 同上，角色目标讨论与 References 中 Riedl & Young 2010 |
| P27 → P38 Dramatron | 同上，方法与实验基线中 Mirowski 等 2023 |
| P28 → P29 Making the Write Connections | [P28 原文](https://zixin.ca/data/pdf/visualstorywriting.pdf)，References [83] |
| P29 → P36 TaleBrush | [P29 原文](https://damienmasson.com/pdfs/writeconnections.pdf)，References [19] |
| P30 → P36 TaleBrush | [P30 原文](https://zixin.ca/data/pdf/Nabakov_s_Cards_C_C_2025.pdf)，相关工作与 References [15] |
| P06 → P08 PersoNet | [P06 原文](https://aclanthology.org/2024.findings-emnlp.499.pdf)，相关工作与 References 中 Yu 等 2023 |
| P06 → P09 LiSCU | 同上，相关工作与 References 中 Brahman 等 2021 |
| P07 → P09 LiSCU | [P07 原文](https://aclanthology.org/2024.findings-emnlp.258.pdf)，Section 2 与 3.2 |
| P07 → P11 Emotion-Aware Storytelling | 同上，Section 2 与 References 中 Brahman & Chaturvedi 2020 |
| P15 → P02 FActScore | [P15 会议原文](https://openreview.net/pdf/4a0a20c0ea48b5f40ceca354794dd00c3b3cd078.pdf)，claim verification 相关工作 |
| P16 → P04 PersonaChat | [P16 原文](https://aclanthology.org/P19-1363.pdf)，引言与数据讨论中 Zhang 等 2018 |
| P20 → P19 InCharacter | [P20 v3 原文](https://arxiv.org/html/2502.09082v3)，Section 5.1、Table 3 与 References |
| P20 → P01 RoleLLM | 同上，数据对照表与 References |
| P22 → P20 CoSER | [P22 v2 原文](https://arxiv.org/html/2603.03915v2)，Section 2 与 References |
| P22 → P19 InCharacter | 同上，引言、评估讨论与 References |
| P22 → P01 RoleLLM | 同上，相关工作与 References |

## 4. 作者网络如何帮助继续找论文

1. **Zixin → Gerald Penn／Tian Yu／Ken Shi → 人物模拟**：先读 P27，再回溯它的方法和基线。最直接连接 P05、P32–P35、P38。
2. **Zixin → Damien Masson／Fanny Chevalier → 可审核的人物与叙事表示**：P28、P29 是共同作者证据；P30 与 P31 扩展到用户控制和关系稳定性。
3. **P27 引用的 Agents’ Room → Mirella Lapata → CHIRON／BookWorm**：P33、P06、P07 都有 Lapata 署名，这是跨群体的作者桥接；不意味着 P27 引用了 P06 或 P07。
4. **LiSCU → Faeze Brahman／Snigdha Chaturvedi → 情绪、人物关系**：P09、P11、P12 的作者重叠提供继续检索入口。[Chaturvedi 的作者目录](https://aclanthology.org/people/snigdha-chaturvedi/) 可用于展开；她不是用户这次指定的校内研究者。
5. **InCharacter → Xintao Wang／Jiangjie Chen／Yanghua Xiao → CoSER**：P19 与 P20 的共同作者及引用已核实；继续关注场景化行为测试。
6. **FABLES → Mohit Iyyer → 动态人物关系**：P15 与 P12 有共同作者，形成“人物关系—长文本忠实性”桥接。

## 5. 当前建议的阅读顺序

不是把 39 篇都读完才开始设计。先做以下 8 篇的精读笔记：

| 顺序 | 论文 | 阅读时必须回答的问题 |
| --- | --- | --- |
| 1 | P27 Multi-Agent Character Simulation | 人物包含哪些字段？目标、记忆、状态如何更新？角色能看到哪些信息？ |
| 2 | P29 Making the Write Connections | 现有工具和用户需求之间缺什么？我们要服务哪类用户任务？ |
| 3 | P06 CHIRON | 人物主张如何生成和过滤？能否保留支持片段与拒绝原因？ |
| 4 | P08 PersoNet | 单次行为怎样结合历史和情境解释？什么时候信息不足？ |
| 5 | P07 BookWorm | description 与 analysis 如何分别定义、检索和评价？ |
| 6 | P02 FActScore | 原子主张是什么粒度？支持率与遗漏率如何分开？ |
| 7 | P25 CAPS | 如何把“稳定人格”表示为跨情境的行为模式？ |
| 8 | P19 InCharacter | 下游人格访谈能验证什么，不能验证什么？ |

随后阅读 P28（审核交互）、P13（证据归因）、P15／P21／P22（评估局限）。RoleLLM 保留为基线参考，当前不再将它排在抽取与表示研究之前。

## 6. 可形成 Schema 假设的研究问题

以下是我们的设计候选，尚未证明有效：

- `claim` 与 `interpretation` 分开；同一证据可以支持多个解释，并可被反证。灵感：P02、P06、P07、P13。
- `source_id`、原文范围、说话者／观察者、人物归属、来源类别、作品版本、故事时间分别记录。不能只保存一个 chunk ID。
- `trait`、`emotion_state`、`goal`、`belief`、`relationship` 分开；不要将一时生气归纳成暴躁人格。灵感：P08、P11、P12、P25、P27。
- `situation → appraisal / goal → behavior` 用于记录情境化模式；先保留原始事例，再决定能否跨情境概括。灵感：P25、P35。
- 区分 `story_time`、`narration_order` 与 `character_knowledge`，防止角色提前知道未来事件。灵感：P27。
- 冲突可能来自事实矛盾、人物成长、观察者不同、同人版本不同或抽取错误；先保留两边，不静默合并。
- `review_status`、用户修正与来源优先级是产品设计假设，应通过用户研究验证；不将其伪称为某篇论文已经给出的标准。

建议把评估拆成：人物归属准确性、主张支持率、关键信息覆盖、冲突识别、情境推断合理性、匿名角色下游行为，以及用户审核成本。人格分数相似不等于人物重建正确。

## 7. 给 Nicole 的讨论问题

1. P27 从人物计划走向故事生成；若反过来从多份文本恢复人物，哪些字段最难恢复，哪些可以可靠保留证据？
2. 如何区分人物稳定特质、临时状态与叙事视角造成的印象？
3. 原著、用户历史互动和第三方分析冲突时，怎样让用户理解并选择目标版本？
4. P28 中的关系图与时间线，哪种形式适合展示“原文支持—模型解释—用户修正”？
5. P27 的未来信息泄漏与自动评估局限，应该怎样转化为我们的小规模对照实验？
6. 她是否建议进一步咨询人物理解、归因评估或文学理论方向的合作者？

## 8. 下一轮搜索与纳入规则

检索入口：ACL Anthology、ACM 论文及作者项目页、arXiv、作者论文目录。主题词包括 character understanding、personality inference、character representation、persona consistency、evidence attribution、narrative time、human-AI creative writing。

对 A 级论文各做一轮向后追溯和向前追踪，记录新增文献的“发现路径”。已核实引用边与仅发现候选链接分开存储。优先纳入能回答具体 Schema／评估问题、有明确任务定义或可检查数据的工作；avatar 渲染、声音生成和纯视觉一致性暂不展开。多来源冲突整合仍是本轮覆盖较薄的部分，需要单独检索来源可信度、矛盾检测与版本管理研究。

本轮扩展已覆盖到 2026 年新近候选；没有穷尽所有前向引用，也没有声称形成系统性综述。
