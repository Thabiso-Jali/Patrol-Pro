<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/Patrol.php';
require_once __DIR__ . '/../models/AuditLog.php';
require_once __DIR__ . '/../models/Notification.php';

final class PatrolController
{
    public function index(): void
    {
        $user = require_auth();
        $model = new Patrol();
        $routes = $model->routes($user);
        foreach ($routes as &$route) {
            $route['checkpoints'] = $model->checkpoints((int) $route['id']);
        }
        json_response(['data' => $routes]);
    }

    public function store(): void
    {
        $user = require_auth(['Admin', 'Supervisor']);
        $data = json_input();
        require_fields($data, ['client_id', 'name', 'site_name']);

        $id = (new Patrol())->createRoute([
            'client_id' => (int) $data['client_id'],
            'name' => clean_string($data['name'], 160),
            'site_name' => clean_string($data['site_name'], 160),
            'description' => clean_string($data['description'] ?? '', 2000),
        ]);
        (new AuditLog())->record((int) $user['id'], 'patrol_route.create', 'patrol_route', $id);
        json_response(['id' => $id], 201);
    }

    public function completeCheckpoint(): void
    {
        $user = require_auth(['Guard', 'Admin', 'Supervisor']);
        $data = json_input();
        require_fields($data, ['shift_id', 'checkpoint_id']);

        $id = (new Patrol())->completeCheckpoint([
            'shift_id' => (int) $data['shift_id'],
            'checkpoint_id' => (int) $data['checkpoint_id'],
            'latitude' => $data['latitude'] ?? null,
            'longitude' => $data['longitude'] ?? null,
            'notes' => clean_string($data['notes'] ?? '', 1000),
        ], (int) $user['id']);
        (new AuditLog())->record((int) $user['id'], 'checkpoint.complete', 'patrol_log', $id);
        json_response(['id' => $id], 201);
    }

    public function destroy(): void
    {
        $user = require_auth(['Admin', 'Supervisor']);
        $id = (int) ($_GET['id'] ?? 0);
        if ($id <= 0) {
            json_response(['error' => 'Patrol route id is required'], 422);
        }
        (new Patrol())->archiveRoute($id);
        (new AuditLog())->record((int) $user['id'], 'patrol_route.archive', 'patrol_route', $id);
        json_response(['ok' => true, 'message' => 'Route archived']);
    }
}
