# AI 赛博 DM 运行镜像
#
# 基础镜像固定 Python 3.11：src/infra/models.py 使用 datetime.UTC（3.11 新增），
# 且全部依赖均有 cp311 manylinux 预编译 wheel，slim(Debian) 无需 gcc/rustc。
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 依赖层单独放置：源码变更时可复用缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 运行所需代码与前端静态资源。
# static/ 必须与 src/ 同级：src/main.py 以 Path(__file__).parent.parent/"static" 解析并挂载 /static，
# 缺失或层级错位会在 import 阶段（StaticFiles check_dir=True）直接崩溃。
COPY src ./src
COPY static ./static

# 运行期可写目录：SQLite 库 /app/data、生图本地缓存 static/generated、TTS 产物 assets/
RUN mkdir -p /app/data /app/static/generated /app/assets

# 非 root 运行；/app 必须可写——init_db() 在模块导入期建库
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

# 数据库落在持久化卷上（四个斜杠 = 绝对路径，否则会随 WORKDIR 漂移）
ENV DATABASE_URL=sqlite:////app/data/campaign.db

EXPOSE 8000
VOLUME ["/app/data", "/app/static/generated"]

# 探活：slim 镜像无 curl，用 python 标准库打 /health（非 200 会抛异常 → 退出码非 0）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# 仓库无入口脚本，端口必须由命令行显式指定（config.APP_PORT 无任何消费方，改它不生效）。
# 保持单进程：ImageQueue / SceneCards / RateLimiter 均为进程内单例，多 worker 会导致状态分裂。
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
