<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class Patrol extends BaseModel
{
    public function routes(array $user): array
    {
        $params = [];
        $sql = 'SELECT pr.*, c.name AS client_name,
                COUNT(DISTINCT cp.id) AS checkpoint_count,
                COUNT(DISTINCT pl.id) AS completed_count
                FROM patrol_routes pr
                JOIN clients c ON c.id = pr.client_id';
        if ($user['role'] === 'Guard') {
            $sql .= ' JOIN shifts s_scope ON s_scope.route_id = pr.id AND s_scope.guard_user_id = :guard_user_id';
            $params['guard_user_id'] = $user['id'];
        }
        $sql .= '
                LEFT JOIN checkpoints cp ON cp.route_id = pr.id
                LEFT JOIN patrol_logs pl ON pl.checkpoint_id = cp.id';
        if ($user['role'] === 'Client') {
            $sql .= ' WHERE pr.client_id = :client_id';
            $params['client_id'] = $user['client_id'];
        }
        $sql .= ' GROUP BY pr.id ORDER BY pr.created_at DESC';
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    public function createRoute(array $data): int
    {
        $stmt = $this->db->prepare(
            'INSERT INTO patrol_routes (client_id, name, site_name, description, status)
             VALUES (:client_id, :name, :site_name, :description, "active")'
        );
        $stmt->execute([
            'client_id' => $data['client_id'],
            'name' => $data['name'],
            'site_name' => $data['site_name'],
            'description' => $data['description'] ?? null,
        ]);
        return (int) $this->db->lastInsertId();
    }

    public function checkpoints(int $routeId): array
    {
        $stmt = $this->db->prepare('SELECT * FROM checkpoints WHERE route_id = :route_id ORDER BY sequence_order');
        $stmt->execute(['route_id' => $routeId]);
        return $stmt->fetchAll();
    }

    public function completeCheckpoint(array $data, int $guardUserId): int
    {
        $stmt = $this->db->prepare(
            'INSERT INTO patrol_logs (shift_id, checkpoint_id, guard_user_id, completed_at, latitude, longitude, status, notes)
             VALUES (:shift_id, :checkpoint_id, :guard_user_id, NOW(), :latitude, :longitude, "completed", :notes)'
        );
        $stmt->execute([
            'shift_id' => $data['shift_id'],
            'checkpoint_id' => $data['checkpoint_id'],
            'guard_user_id' => $guardUserId,
            'latitude' => $data['latitude'] ?? null,
            'longitude' => $data['longitude'] ?? null,
            'notes' => $data['notes'] ?? null,
        ]);
        return (int) $this->db->lastInsertId();
    }

    public function archiveRoute(int $id): void
    {
        $stmt = $this->db->prepare('UPDATE patrol_routes SET status = "paused" WHERE id = :id');
        $stmt->execute(['id' => $id]);
    }
}
