<?php
declare(strict_types=1);

function start_secure_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }

    $config = require __DIR__ . '/../config/config.php';
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => !empty($_SERVER['HTTPS']) || $config['env'] === 'production',
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    session_start();
}

function current_user(): ?array
{
    start_secure_session();
    $config = require __DIR__ . '/../config/config.php';
    $timeout = $config['session_timeout_minutes'] * 60;

    if (isset($_SESSION['last_seen']) && time() - (int) $_SESSION['last_seen'] > $timeout) {
        session_destroy();
        return null;
    }
    $_SESSION['last_seen'] = time();

    return $_SESSION['user'] ?? null;
}

function require_auth(array $roles = []): array
{
    $user = current_user();
    if (!$user) {
        json_response(['error' => 'Authentication required'], 401);
    }
    if ($roles && !in_array($user['role'], $roles, true)) {
        json_response(['error' => 'Insufficient permissions'], 403);
    }
    return $user;
}

function sign_in(array $user): void
{
    start_secure_session();
    session_regenerate_id(true);
    $_SESSION['user'] = [
        'id' => (int) $user['id'],
        'name' => $user['name'],
        'email' => $user['email'],
        'role' => $user['role'],
        'client_id' => $user['client_id'] ? (int) $user['client_id'] : null,
    ];
    $_SESSION['last_seen'] = time();
}

function sign_out(): void
{
    start_secure_session();
    $_SESSION = [];
    session_destroy();
}
