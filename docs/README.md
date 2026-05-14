# 项目文档中心 (Documentation Hub)

本项目严格遵循 **Spec-Driven Development (规格驱动开发)** 模式，所有设计、开发、测试均以各目录下的 `spec.md` 或等效规范文档为准绳。

## 目录结构说明

```text
docs/
├── README.md                      <-- 本文档导航
├── product-specs/                 <-- [需求规格] 产品需求文档 (PRD/Spec)
├── design-docs/                   <-- [架构设计] 系统总设、模块详设、ADR
├── api-contracts/                 <-- [API 契约] RESTful 接口、事件结构契约
├── testing/                       <-- [测试规范] 测试计划、用例、测试报告
├── operations/                    <-- [运维手册] 部署指南、SOP/Runbook
└── pic/                           <-- [资源] 全局通用的图片、流程图等资源
```

## Spec 模式工作流指南
1. **需求阶段**：在 `product-specs/` 编写业务需求的 `spec.md`。
2. **设计阶段**：在 `design-docs/` 完善总设和各子模块的技术级 `spec.md` 及领域模型。
3. **契约阶段**：在 `api-contracts/` 定义前后端及服务间交互的 API 和 Event 格式。
4. **测试阶段**：在 `testing/` 基于前述 Spec 编写验收测试计划。
5. **开发阶段**：基于以上文档执行代码生成和评审闭环。