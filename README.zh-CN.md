<h1 align="center">FitGirl Repacks - FuckingFast 批量下载器</h1>
<p align="center">
  <b>自动批量下载 FitGirl Repacks 页面上 FuckingFast 托管的所有 .rar 分卷</b><br>
  <a href="#使用方法">使用方法</a> •
  <a href="#功能特性">功能特性</a> •
  <a href="#参数说明">参数说明</a> •
  <a href="#工作原理">工作原理</a><br>
  <a href="README.md">English</a> | 简体中文
</p>

---

FitGirl Repacks 网站上大型游戏会被拆分成上百个 `.rar` 分卷，手动逐个点击下载极其痛苦。这个工具可以自动批量下载 FuckingFast 文件托管上的所有分卷。

## 功能特性

- **批量下载** - 自动解析页面，提取所有 FuckingFast 下载链接
- **断点续传** - 中断后重新运行，自动从断点继续下载
- **失败重试** - 单个文件下载失败自动重试（默认 3 次，递增等待）
- **完整性校验** - 下载后校验文件大小，防止静默截断
- **并行下载** - 支持多线程并行下载，充分利用带宽
- **灵活过滤** - 按 part 范围、正则表达式、可选组件等多种方式筛选文件
- **零依赖** - 纯 Python 标准库，无需安装任何第三方包

## 环境要求

- Python 3.12+

## 使用方法

```bash
# 列出所有文件（不下载）
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --list-only

# 下载全部文件到指定目录
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -o ~/Downloads/bmw

# 跳过可选内容（原声带等）
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -o ~/Downloads/bmw --skip-optional

# 只下载 part 5 到 part 10
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --start 5 --end 10

# 3 个并行下载
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -p 3

# 正则过滤文件名
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --filter "part00[1-5]"

# 网络不稳定时增加重试次数
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -r 5
```

## 参数说明

| 参数 | 说明 |
|---|---|
| `-o, --output DIR` | 下载目录（默认当前目录） |
| `-p, --parallel N` | 并行下载数（默认 2） |
| `-l, --list-only` | 只列出文件，不下载 |
| `-f, --filter REGEX` | 正则过滤文件名 |
| `--skip-optional` | 跳过可选组件（原声带等） |
| `--start N` | 从 part N 开始下载 |
| `--end N` | 下载到 part N 为止 |
| `-r, --retry N` | 失败重试次数（默认 3） |

## 工作原理

1. 抓取 FitGirl Repacks 游戏页面 HTML
2. 解析出所有 `fuckingfast.co` 文件链接
3. 逐个访问 FuckingFast 页面，从内嵌 JavaScript 中提取真实下载直链（`/dl/` URL）
4. 通过直链下载文件，支持断点续传和自动重试

## 注意事项

- FuckingFast 的 `/dl/` token 有时效性，重试时会自动重新获取
- 建议并行数不要设太高（2-3 即可），避免被服务器限流
- 下载中断后直接重新运行相同命令即可，已完成的文件会自动跳过
