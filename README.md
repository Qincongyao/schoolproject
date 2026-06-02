# 校园学生作品展示网站

基于 Python Flask 的校园学生作品展示平台，包含首页、滚动画廊、作品档案库（分类 + 搜索）、结构化投稿模板，以及管理员登录与审核功能。

## 功能

- **首页**：精选作品 + 滚动画廊、平台统计、参与指引
- **作品档案库**：五大分类筛选、关键词与标签搜索、相似作品推荐
- **作品详情**：多图、创作说明、论文/GitHub/视频链接（如有）
- **用户系统**：注册/登录后投稿，查看我的投稿
- **投稿模板**：作品信息、标签、选填链接（论文/GitHub/视频）、作者信息（含年级）
- **中英文切换**：导航栏「中 | EN」切换界面语言
- **管理后台**：须点击进入审核页，支持通过/拒绝/隐藏/删除

## 快速开始

```bash
cd campus-gallery
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

浏览器访问：http://127.0.0.1:5001

> macOS 上 5000 端口常被 AirPlay Receiver 占用，本项目默认使用 **5001**。如需换端口：`PORT=8080 python run.py`

### 默认管理员账号

| 项目 | 默认值 |
|------|--------|
| 用户名 | `admin` |
| 密码 | `admin123` |

生产环境请通过环境变量修改：

```bash
export ADMIN_USERNAME=your_admin
export ADMIN_PASSWORD=your_secure_password
export SECRET_KEY=your-random-secret-key
```

## 项目结构

```
campus-gallery/
├── app.py              # 应用入口与路由
├── config.py           # 配置
├── models.py           # 数据模型
├── run.py              # 启动脚本
├── requirements.txt
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/        # 上传图片目录
└── templates/          # 页面模板
```

## 投稿模板字段

**作品信息**：标题、分类、标签、简介、创作说明、图片（至少 1 张）

**相关链接（选填）**：论文链接、GitHub 链接、演示视频链接

**作者信息**：姓名、学号、年级、联系方式（仅管理员可见）

**作品分类**：智能硬件与机器人 · 软件开发与人工智能 · 生命科学与环境 · 社会科学与创意设计 · 工程与物理

投稿状态：`pending` → 管理员审核 → `approved`（公开展示）或 `rejected`
