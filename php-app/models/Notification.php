<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class Notification extends BaseModel
{
    public function list(int $userId): array
    {
        $stmt = $this->db->prepare(
            'SELECT * FROM notifications
             WHERE user_id IS NULL OR user_id = :user_id
             ORDER BY created_at DESC
             LIMIT 100'
        );
        $stmt->execute(['user_id' => $userId]);
        return $stmt->fetchAll();
    }

    public function create(?int $userId, string $title, string $body, string $type): void
    {
        $stmt = $this->db->prepare(
            'INSERT INTO notifications (user_id, title, body, type)
             VALUES (:user_id, :title, :body, :type)'
        );
        $stmt->execute([
            'user_id' => $userId,
            'title' => $title,
            'body' => $body,
            'type' => $type,
        ]);
    }

    public function markRead(int $id, int $userId): void
    {
        $stmt = $this->db->prepare(
            'UPDATE notifications SET read_at = NOW()
             WHERE id = :id AND (user_id = :user_id OR user_id IS NULL)'
        );
        $stmt->execute(['id' => $id, 'user_id' => $userId]);
    }
}
