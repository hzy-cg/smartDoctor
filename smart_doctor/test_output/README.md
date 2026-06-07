# 测试输出目录说明

## 目录结构

```
test_output/
├── reports/        # 测试报告 (Markdown/HTML)
├── results/        # 测试运行结果 (文本日志)
├── screenshots/    # UI自动化测试截图
└── coverage/       # 覆盖率数据 (.coverage, HTML报告)
```

## 用途

- `reports/` — 存放测试报告、缺陷追踪文档
- `results/` — 存放 pytest 运行输出的文本日志
- `screenshots/` — 存放 Playwright/UI 自动化测试的截图
- `coverage/` — 存放覆盖率数据文件和 HTML 覆盖率报告

## 生成命令

```bash
# 生成覆盖率报告到 coverage/html/
pytest tests/ --cov=app --cov-report=html:test_output/coverage/html

# 生成测试结果日志
pytest tests/ -v > test_output/results/run_$(date +%Y%m%d_%H%M%S).txt

# 生成JUnit XML报告
pytest tests/ --junitxml=test_output/results/junit.xml
```
