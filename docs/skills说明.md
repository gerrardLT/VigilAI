开发流程类

brainstorming：做功能前先发散方案，避免一上来就写死。
writing-plans：把需求拆成可执行计划。
executing-plans：按已有计划推进实现。
test-driven-development：先补测试再写功能。
systematic-debugging：系统化排查 bug，不靠猜。
verification-before-completion：交付前强制做验证。
requesting-code-review：完成后做正式代码审查。
receiving-code-review：处理 review 意见时用。
dispatching-parallel-agents：适合并行拆任务。
subagent-driven-development：多子任务协同开发。
using-git-worktrees：隔离分支/工作树开发。
finishing-a-development-branch：收尾、整理、准备合并。
前端设计/UI 类

frontend-design：做高质量前端界面，不要 AI 味太重。
audit：做前端技术审计，查可访问性、响应式、主题、性能、反模式。
adapt：适配移动端、不同屏幕。
arrange：优化布局、间距、层级。
animate：补动效和微交互。
bolder：把设计做得更有冲击力。
colorize：优化配色。
clarify：优化文案、提示语、按钮文案。
critique：从 UX 角度批判性评估设计。
delight：增加细节和惊喜感。
distill：删繁就简，压缩冗余设计。
extract：抽设计 token、通用组件。
harden：补边界处理、异常态、i18n、溢出问题。
normalize：统一设计规范和组件风格。
onboard：做新手引导、空状态、首次使用路径。
optimize：查前端性能。
overdrive：做更激进、更高级的视觉/交互实现。
polish：最后一轮精修。
quieter：把太吵的设计收敛。
typeset：优化字体、字号、排版层次。
文档/能力扩展类

openai-docs：查 OpenAI 官方文档。
skill-creator：创建新 skill。
skill-installer：安装 skill。
find-skills：帮你找适合任务的 skill。
writing-skills：编写/改造 skill 本身。
plugin-creator：创建插件。
document-release：发布后同步更新文档。
浏览器/QA/发布类

browse：无头浏览器测试页面。
qa：系统化跑 QA 并修问题。
qa-only：只做 QA 报告，不改代码。
benchmark：做性能基准测试。
canary：发布后线上巡检。
health：代码质量体检。
review：预发布代码审查。
ship：测试、变更记录、发版流程。
land-and-deploy：合并并部署。
setup-deploy：配置部署环境。
setup-browser-cookies：导入浏览器 cookie 做登录态测试。
connect-chrome：连接真实 Chrome 做可视化调试。
安全/约束/排查类

careful：危险命令保护。
guard：更严格的安全保护。
freeze：限制只能改某个目录。
unfreeze：解除目录限制。
investigate：做深入问题调查。
cso：安全审计模式。
产品/策略/复盘类

office-hours：偏创业/产品策略拷问。
retro：复盘工程过程。
learn：管理项目长期经验记录。
checkpoint：保存当前工作上下文。
plan-ceo-review：从老板/产品视角审计划。
plan-design-review：从设计视角审计划。
plan-eng-review：从工程视角审计划。
autoplan：自动串联 CEO/设计/工程评审。
其他

imagegen：生成或编辑图片。
agent-reach：扩展外部信息获取能力。
teach-impeccable：建立项目设计上下文，供设计类 skill 使用。