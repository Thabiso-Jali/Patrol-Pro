<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class Incident extends BaseModel
{
    public function list(array $user, array $filters): array
    {
        $params = [];
        $sql = 'SELECT i.*, u.name AS guard_name, c.name AS client_name, pr.site_name
                FROM incidents i
                JOIN users u ON u.id = i.guard_user_id
                JOIN clients c ON c.id = i.client_id
                LEFT JOIN patrol_routes pr ON pr.id = i.route_id
                WHERE 1=1';
        if ($user['role'] === 'Client') {
            $sql .= ' AND i.client_id = :client_id';
            $params['client_id'] = $user['client_id'];
        } elseif ($user['role'] === 'Guard') {
            $sql .= ' AND i.guard_user_id = :guard_user_id';
            $params['guard_user_id'] = $user['id'];
        }
        if (!empty($filters['status'])) {
            $sql .= ' AND i.status = :status';
            $params['status'] = $filters['status'];
        }
        if (!empty($filters['date'])) {
            $sql .= ' AND DATE(i.reported_at) = :date';
            $params['date'] = $filters['date'];
        }
        $sql .= ' ORDER BY i.reported_at DESC LIMIT 200';
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    public function create(array $data, int $guardUserId): int
    {
        $stmt = $this->db->prepare(
            'INSERT INTO incidents
             (client_id, route_id, guard_user_id, category, severity, title, notes, evidence_path, latitude, longitude, status, reported_at)
             VALUES
             (:client_id, :route_id, :guard_user_id, :category, :severity, :title, :notes, :evidence_path, :latitude, :longitude, "open", NOW())'
        );
        $stmt->execute([
            'client_id' => $data['client_id'],
            'route_id' => $data['route_id'] ?? null,
            'guard_user_id' => $guardUserId,
            'category' => $data['category'],
            'severity' => $data['severity'] ?? 'medium',
            'title' => $data['title'],
            'notes' => $data['notes'] ?? null,
            'evidence_path' => $data['evidence_path'] ?? null,
            'latitude' => $data['latitude'] ?? null,
            'longitude' => $data['longitude'] ?? null,
        ]);
        return (int) $this->db->lastInsertId();
    }

    public function delete(int $id): void
    {
        $stmt = $this->db->prepare('DELETE FROM incidents WHERE id = :id');
        $stmt->execute(['id' => $id]);
    }
}
