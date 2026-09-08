# 方法来源与维护

核验日期：2026-09-08。以下为原始文档、论文与公开实现。内容采用原创归纳，不捆绑第三方代码或完整文档。本文献支持特定做法，不代表本 Skill 已获得同等实验效果。

| 标识 | 来源 | 用于什么 |
| --- | --- | --- |
| S1 | [OpenAI: Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) | 清楚目标与约束；推理模型不必强制展示逐步思考；按需要采用示例 |
| S2 | [Anthropic: Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) | 明确指令、上下文、示例、复杂任务分解与避免越界扩张 |
| S3 | [OpenAI: Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) | 生成与编辑、输入图像和编辑机制的区别；具体模型能力需重新核验 |
| S4 | [Google: Video generation best practices](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/best-practice) | 视频场景组织，图生视频关注运动的工具特定建议 |
| S5 | [OpenAI: Prompt optimizer](https://developers.openai.com/api/docs/guides/prompt-optimizer) | 用输出、反馈和评估驱动优化；优化版本仍可能退步。仅借鉴方法，不依赖该托管平台 |
| S6 | [LangMem: Core concepts](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/) | 区分偏好、经历与行为方法，考虑记忆形成和检索 |
| S7 | [ACE: Agentic Context Engineering](https://arxiv.org/html/2510.04618v1) | 按条目渐进更新、提炼与整理经验，避免整篇重写丢失细节 |
| S8 | [pskoett self-improvement Skill](https://github.com/pskoett/pskoett-ai-skills/blob/main/skills/self-improvement/SKILL.md) | 捕捉纠正与重复模式，将积累的经验转成后续指导 |
| S9 | [Agent Skills client implementation](https://agentskills.io/client-implementation/adding-skills-support) | 按需加载资源；宿主负责发现、执行与可访问能力 |

另参考了 [Prompt Master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 的目标工具路由与上下文携带、[PromptShift](https://github.com/Alvaro-Manzo/promptshift/blob/main/SKILL.md) 的最小改写原则，以及 [linshenkx/prompt-optimizer](https://github.com/linshenkx/prompt-optimizer) 的结果对比工作方式。没有照搬其模板、参数表、代码或效果主张。

## 维护规则

稳定的判断方法留在知识参考中。版本、参数、输入限制等易变信息用官方来源核验，并把工具与日期写入案例。没有验证时不要补造兼容性结论。失效链接只标记为待复核，不能自行编造替代文档。

个人经验不自动变成公共资料。公开新版本时仅使用合成案例、作者自有素材或用户明确同意公开的材料，并保留必要来源信息。
