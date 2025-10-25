
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（分步，便于诊断，适配arm64）
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    exiftool
RUN rm -rf /var/lib/apt/lists/*

# 复制项目文件（可根据实际情况优化为分阶段COPY）
COPY . /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露API端口
EXPOSE 5156

# 设置环境变量（可根据需要调整）
ENV HOST=0.0.0.0
ENV PORT=5156

# 以非root用户运行（安全性考虑）
RUN useradd -m superbird && chown -R superbird:superbird /app
USER superbird

# 启动API服务
CMD ["python", "SuperBirdID_API.py", "--host", "0.0.0.0", "--port", "5156"]


VOLUME ["/photo"]
