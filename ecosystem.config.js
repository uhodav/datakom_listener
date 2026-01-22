module.exports = {
  apps: [
    {
      name: 'datakom-listener',
      script: 'datakom_listener.py',
      interpreter: 'python3',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        DATAKOM_LANG: 'uk'
      },
      error_file: './logs/listener-error.log',
      out_file: './logs/listener-out.log',
      log_file: './logs/listener-combined.log',
      time: true,
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      // Log rotation
      max_size: '5M',
      retain: 10,
      compress: true,
      dateFormat: 'YYYY-MM-DD_HH-mm-ss',
      rotateInterval: '0 0 * * *',
      rotateModule: true
    },
    {
      name: 'datakom-api',
      script: 'api_server.py',
      interpreter: 'python3',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        DATAKOM_LANG: 'uk'
      },
      error_file: './logs/api-error.log',
      out_file: './logs/api-out.log',
      log_file: './logs/api-combined.log',
      time: true,
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      // Log rotation
      max_size: '5M',
      retain: 10,
      compress: true,
      dateFormat: 'YYYY-MM-DD_HH-mm-ss',
      rotateInterval: '0 0 * * *',
      rotateModule: true
    }
  ]
};
