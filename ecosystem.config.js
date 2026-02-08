module.exports = {
    apps: [{
      name: "my-hosting-bot",
      script: "main.py",
      args: "telegram",
      instances: 1,
      watch: true,
      env: {
        NODE_ENV: "development",
      },
      env_production: {
        NODE_ENV: "production",
      }
    }]
};