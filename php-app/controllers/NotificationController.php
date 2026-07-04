<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/Notification.php';

final class NotificationController
{
    public function index(): void
    {
        $user = require_auth();
        json_response(['data' => (new Notification())->list((int) $user['id'])]);
    }

    public function markRead(): void
    {
        $user = require_auth();
        $data = json_input();
        require_fields($data, ['id']);
        (new Notification())->markRead((int) $data['id'], (int) $user['id']);
        json_response(['ok' => true]);
    }
}
