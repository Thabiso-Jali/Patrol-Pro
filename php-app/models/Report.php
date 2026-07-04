<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class Report extends BaseModel
{
    public function daily(array $user, string $date): array
    {
        $params = ['date' => $date];
        $clientClause = '';
        if ($user['role'] === 'Client') {
            $clientClause = ' AND pr.client_id = :client_id';
            $params['client_id'] = $user['client_id'];
        } elseif ($user['role'] === 'Guard') {
            $clientClause = ' AND pl.guard_user_id = :guard_user_id';
            $params['guard_user_id'] = $user['id'];
        }

        $stmt = $this->db->prepare(
            'SELECT pr.site_name, pr.name AS route_name, u.name AS guard_name,
                    COUNT(pl.id) AS completed_checkpoints
             FROM patrol_logs pl
             JOIN shifts s ON s.id = pl.shift_id
             JOIN patrol_routes pr ON pr.id = s.route_id
             JOIN users u ON u.id = pl.guard_user_id
             WHERE DATE(pl.completed_at) = :date' . $clientClause . '
             GROUP BY pr.id, u.id'
        );
        $stmt->execute($params);
        $patrols = $stmt->fetchAll();

        $incidentStmt = $this->db->prepare(
            'SELECT i.title, i.category, i.severity, i.status, i.reported_at, pr.site_name
             FROM incidents i
             LEFT JOIN patrol_routes pr ON pr.id = i.route_id
             WHERE DATE(i.reported_at) = :date' . $clientClause . '
             ORDER BY i.reported_at DESC'
        );
        $incidentStmt->execute($params);

        return [
            'date' => $date,
            'patrols' => $patrols,
            'incidents' => $incidentStmt->fetchAll(),
        ];
    }
}
