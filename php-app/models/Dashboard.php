<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class Dashboard extends BaseModel
{
    public function summary(array $user): array
    {
        if ($user['role'] === 'Client') {
            $clientParams = ['client_id' => $user['client_id']];
            return [
                'total_guards' => 0,
                'active_patrols' => $this->count('SELECT COUNT(*) FROM patrol_routes pr WHERE pr.status = "active" AND pr.client_id = :client_id', $clientParams),
                'open_incidents' => $this->count('SELECT COUNT(*) FROM incidents i WHERE i.status <> "resolved" AND i.client_id = :client_id', $clientParams),
                'completed_shifts' => $this->count('SELECT COUNT(*) FROM shifts s JOIN patrol_routes pr ON pr.id = s.route_id WHERE s.status = "completed" AND pr.client_id = :client_id', $clientParams),
                'activity' => [],
            ];
        }

        if ($user['role'] === 'Guard') {
            $guardParams = ['guard_user_id' => $user['id']];
            return [
                'total_guards' => 1,
                'active_patrols' => $this->count('SELECT COUNT(*) FROM shifts WHERE guard_user_id = :guard_user_id AND status IN ("scheduled", "active")', $guardParams),
                'open_incidents' => $this->count('SELECT COUNT(*) FROM incidents WHERE guard_user_id = :guard_user_id AND status <> "resolved"', $guardParams),
                'completed_shifts' => $this->count('SELECT COUNT(*) FROM shifts WHERE guard_user_id = :guard_user_id AND status = "completed"', $guardParams),
                'activity' => $this->activity($user),
            ];
        }

        return [
            'total_guards' => $this->count('SELECT COUNT(*) FROM users JOIN roles ON roles.id = users.role_id WHERE roles.name = "Guard"'),
            'active_patrols' => $this->count('SELECT COUNT(*) FROM patrol_routes pr WHERE pr.status = "active"'),
            'open_incidents' => $this->count('SELECT COUNT(*) FROM incidents i WHERE i.status <> "resolved"'),
            'completed_shifts' => $this->count('SELECT COUNT(*) FROM shifts s WHERE s.status = "completed"'),
            'activity' => $this->activity($user),
        ];
    }

    private function count(string $sql, array $params = []): int
    {
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return (int) $stmt->fetchColumn();
    }

    private function activity(array $user): array
    {
        $params = [];
        $sql = 'SELECT action, entity_type, detail, created_at FROM audit_logs WHERE action = "auth.login"';
        if ($user['role'] === 'Guard') {
            $sql .= ' AND user_id = :user_id';
            $params['user_id'] = $user['id'];
        }
        $sql .= ' ORDER BY created_at DESC LIMIT 5';
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }
}
