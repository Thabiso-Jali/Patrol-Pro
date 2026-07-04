<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/User.php';
require_once __DIR__ . '/../models/AuditLog.php';

final class AuthController
{
    public function login(): void
    {
        $data = json_input();
        require_fields($data, ['email', 'password']);

        $user = (new User())->findByEmail(clean_string($data['email'], 160));
        if (!$user || !password_verify((string) $data['password'], $user['password_hash'])) {
            json_response(['error' => 'Invalid email or password'], 401);
        }

        sign_in($user);
        (new AuditLog())->record((int) $user['id'], 'auth.login', 'user', (int) $user['id']);
        json_response(['user' => current_user()]);
    }

    public function logout(): void
    {
        $user = current_user();
        if ($user) {
            (new AuditLog())->record((int) $user['id'], 'auth.logout', 'user', (int) $user['id']);
        }
        sign_out();
        json_response(['ok' => true]);
    }

    public function me(): void
    {
        json_response(['user' => current_user()]);
    }
}
