module.exports = {
  devServer: {
    proxy: {
      "/api": { target: "http://localhost:8080", changeOrigin: true },
      "/agent-api": {
        target: process.env.AGENT_SERVICE_URL || "http://127.0.0.1:8001",
        changeOrigin: true,
        pathRewrite: { "^/agent-api": "/api" }
      }
    }
  }
};
