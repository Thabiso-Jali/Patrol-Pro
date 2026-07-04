<?php
declare(strict_types=1);

$root = dirname(__DIR__);
require_once __DIR__ . '/env.php';
load_env($root . '/.env');

$env = env_value('APP_ENV', 'local') ?? 'local';
$isProduction = $env === 'production';

$requiredInProduction = ['APP_URL', 'DB_HOST', 'DB_DATABASE', 'DB_USERNAME', 'DB_PASSWORD'];
foreach ($requiredInProduction as $key) {
    if ($isProduction && env_value($key) === null) {
        throw new RuntimeException("Missing required production environment variable: {$key}");
    }
}

return [
    'app_name' => env_value('APP_NAME', 'Patrol Pro'),
    'app_url' => rtrim(env_value('APP_URL', 'http://127.0.0.1:8080') ?? 'http://127.0.0.1:8080', '/'),
    'env' => $env,
    'debug' => filter_var(env_value('APP_DEBUG', $isProduction ? 'false' : 'true'), FILTER_VALIDATE_BOOLEAN),
    'session_timeout_minutes' => max(5, (int) (env_value('SESSION_TIMEOUT_MINUTES', '30') ?? 30)),
    'upload_dir' => env_value('UPLOAD_DIR', $root . '/public/uploads/incidents'),
    'max_upload_mb' => max(1, (int) (env_value('MAX_UPLOAD_MB', '5') ?? 5)),
    'db' => [
        'host' => env_value('DB_HOST', '127.0.0.1'),
        'port' => env_value('DB_PORT', '3306'),
        'database' => env_value('DB_DATABASE', 'patrol_pro'),
        'username' => env_value('DB_USERNAME', 'root'),
        'password' => env_value('DB_PASSWORD', ''),
        'charset' => env_value('DB_CHARSET', 'utf8mb4'),
    ],
];
