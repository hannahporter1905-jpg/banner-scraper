FROM node:18-slim

# Install system dependencies:
# - dumb-init: proper PID1 signal handling for containers
# - python3 + python-is-python3: scraper engine + 'python' symlink for spawn()
# - Chromium system libs required by Playwright
RUN apt-get update && apt-get install -y \
    dumb-init \
    python3 \
    python3-pip \
    python-is-python3 \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests separately to leverage Docker layer cache
COPY package.json requirements.txt ./
COPY backend/package.json backend/package-lock.json ./backend/

# Install Node.js dependencies
RUN npm install --prefix backend

# Install Python dependencies
RUN pip3 install --break-system-packages -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Cloud Run listens on 8080
EXPOSE 8080

ENV NODE_ENV=production
ENV PORT=8080

# dumb-init as PID1 for clean signal forwarding and zombie reaping
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "backend/server-playwright.js"]
