<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/Shift.php';
require_once __DIR__ . '/../models/AuditLog.php';
require_once __DIR__ . '/../models/Notification.php';

final class ShiftController
{
    public function index(): void
    {
        $user = require_auth();
        json_response(['data' => (new Shift())->list($user)]);
    }

    public function store(): void
    {
        $user = require_auth(['Admin', 'Supervisor']);
        $data = json_input();
        require_fields($data, ['guard_user_id', 'route_id', 'starts_at', 'ends_at']);
        $id = (new Shift())->create([
            'guard_user_id' => (int) $data['guard_user_id'],
            'route_id' => (int) $data['route_id'],
            'starts_at' => clean_string($data['starts_at'], 40),
            'ends_at' => clean_string($data['ends_at'], 40),
        ]);
        (new Notification())->create((int) $data['guard_user_id'], 'New shift assigned', 'A supervisor assigned you a patrol shift.', 'shift');
        (new AuditLog())->record((int) $user['id'], 'shift.create', 'shift', $id);
        json_response(['id' => $id], 201);
    }

    public function destroy(): void
    {
        $user = require_auth(['Admin', 'Supervisor']);
        $id = (int) ($_GET['id'] ?? 0);
        if ($id <= 0) {
            json_response(['error' => 'Shift id is required'], 422);
        }
        (new Shift())->delete($id);
        (new AuditLog())->record((int) $user['id'], 'shift.delete', 'shift', $id);
        json_response(['ok' => true]);
    }

    public function start(): void
    {
        $user = require_auth(['Admin', 'Supervisor', 'Guard']);
        $id = $this->shiftIdFromRequest();
        (new Shift())->start($id, $user);
        (new AuditLog())->record((int) $user['id'], 'shift.start', 'shift', $id);
        json_response(['ok' => true]);
    }

    public function clockOut(): void
    {
        $user = require_auth(['Admin', 'Supervisor', 'Guard']);
        $id = $this->shiftIdFromRequest();
        (new Shift())->clockOut($id, $user);
        (new AuditLog())->record((int) $user['id'], 'shift.clock_out', 'shift', $id);
        json_response(['ok' => true]);
    }

    private function shiftIdFromRequest(): int
    {
        $data = json_input();
        $id = (int) ($data['id'] ?? $_GET['id'] ?? 0);
        if ($id <= 0) {
            json_response(['error' => 'Shift id is required'], 422);
        }
        return $id;
    }
}
