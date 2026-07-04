<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/User.php';
require_once __DIR__ . '/../models/AuditLog.php';

final class GuardController
{
    public function index(): void
    {
        require_auth(['Admin', 'Supervisor']);
        $search = isset($_GET['search']) ? clean_string($_GET['search'], 120) : null;
        json_response(['data' => (new User())->guards($search)]);
    }

    public function store(): void
    {
        $user = require_auth(['Admin']);
        $data = json_input();
        require_fields($data, ['name', 'email', 'password', 'badge_number']);
        if (!filter_var($data['email'], FILTER_VALIDATE_EMAIL)) {
            json_response(['error' => 'Invalid email address'], 422);
        }

        $id = (new User())->createGuard([
            'name' => clean_string($data['name'], 160),
            'email' => clean_string($data['email'], 160),
            'password' => (string) $data['password'],
            'phone' => clean_string($data['phone'] ?? '', 60),
            'badge_number' => clean_string($data['badge_number'], 80),
            'certification' => clean_string($data['certification'] ?? '', 160),
            'emergency_contact' => clean_string($data['emergency_contact'] ?? '', 160),
        ]);
        (new AuditLog())->record((int) $user['id'], 'guard.create', 'user', $id);
        json_response(['id' => $id], 201);
    }

    public function destroy(): void
    {
        $user = require_auth(['Admin']);
        $id = (int) ($_GET['id'] ?? 0);
        if ($id <= 0) {
            json_response(['error' => 'Guard id is required'], 422);
        }
        (new User())->deactivateGuard($id);
        (new AuditLog())->record((int) $user['id'], 'guard.deactivate', 'user', $id);
        json_response(['ok' => true, 'message' => 'Guard deactivated']);
    }
}
