<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class AuditLog extends BaseModel
{
    public function record(?int $userId, string $action, string $entity, ?int $entityId = null, ?string $detail = null): void
    {
        $stmt = $this->db->prepare(
            'INSERT INTO audit_logs (user_id, action, entity_type, entity_id, detail, ip_address, created_at)
             VALUES (:user_id, :action, :entity_type, :entity_id, :detail, :ip_address, NOW())'
        );
        $stmt->execute([
            'user_id' => $userId,
            'action' => $action,
            'entity_type' => $entity,
            'entity_id' => $entityId,
            'detail' => $detail,
            'ip_address' => $_SERVER['REMOTE_ADDR'] ?? null,
        ]);
    }
}
