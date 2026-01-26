# Development image
FROM node:20-alpine

WORKDIR /app

# 安装pnpm
RUN npm install -g pnpm

# 复制package文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 复制源代码
COPY . .

EXPOSE 5173

ENV NODE_ENV=development \
    HOST=0.0.0.0

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
