<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class Shift extends BaseModel
{
    public function list(array $user): array
    {
        $params = [];
        $sql = 'SELECT s.*, u.name AS guard_name, pr.name AS route_name, pr.site_name
                FROM shifts s
                JOIN users u ON u.id = s.guard_user_id
                JOIN patrol_routes pr ON pr.id = s.route_id';
        if ($user['role'] === 'Client') {
            $sql .= ' WHERE pr.client_id = :client_id';
            $params['client_id'] = $user['client_id'];
        } elseif ($user['role'] === 'Guard') {
            $sql .= ' WHERE s.guard_user_id = :guard_user_id';
            $params['guard_user_id'] = $user['id'];
        }
        $sql .= ' ORDER BY s.starts_at DESC LIMIT 200';
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    public function create(array $data): int
    {
        $stmt = $this->db->prepare(
            'INSERT INTO shifts (guard_user_id, route_id, starts_at, ends_at, status)
             VALUES (:guard_user_id, :route_id, :starts_at, :ends_at, "scheduled")'
        );
        $stmt->execute([
            'guard_user_id' => $data['guard_user_id'],
            'route_id' => $data['route_id'],
            'starts_at' => $data['starts_at'],
            'ends_at' => $data['ends_at'],
        ]);
        return (int) $this->db->lastInsertId();
    }

    public function start(int $id, array $user): void
    {
        $this->changeStatus($id, $user, 'scheduled', 'active');
    }

    public function clockOut(int $id, array $user): void
    {
        $this->changeStatus($id, $user, 'active', 'completed');
    }

    public function delete(int $id): void
    {
        $stmt = $this->db->prepare('DELETE FROM shifts WHERE id = :id');
        $stmt->execute(['id' => $id]);
    }

    private function changeStatus(int $id, array $user, string $from, string $to): void
    {
        $params = [
            'id' => $id,
            'from_status' => $from,
            'to_status' => $to,
        ];
        $sql = 'UPDATE shifts SET status = :to_status WHERE id = :id AND status = :from_status';

        if ($user['role'] === 'Guard') {
            $sql .= ' AND guard_user_id = :guard_user_id';
            $params['guard_user_id'] = $user['id'];
        }

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);

        if ($stmt->rowCount() === 0) {
            json_response(['error' => 'Shift is not available for this action'], 409);
        }
    }
}
