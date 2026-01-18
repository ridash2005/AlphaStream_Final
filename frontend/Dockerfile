# Frontend Dockerfile
FROM node:18-slim

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Build for production
RUN npm run build

# Install serve to run the build
RUN npm install -g serve

# Expose port
EXPOSE 5173

# Serve the build
CMD ["serve", "-s", "dist", "-l", "5173"]
