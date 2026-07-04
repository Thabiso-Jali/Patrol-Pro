<?php
declare(strict_types=1);

require_once __DIR__ . '/BaseModel.php';

final class User extends BaseModel
{
    public function findByEmail(string $email): ?array
    {
        $stmt = $this->db->prepare(
            'SELECT users.*, roles.name AS role
             FROM users
             JOIN roles ON roles.id = users.role_id
             WHERE users.email = :email AND users.status = "active"
             LIMIT 1'
        );
        $stmt->execute(['email' => $email]);
        $user = $stmt->fetch();
        return $user ?: null;
    }

    public function guards(?string $search = null): array
    {
        $sql = 'SELECT users.id, users.name, users.email, users.status, gp.phone, gp.badge_number, gp.certification
                FROM users
                JOIN roles ON roles.id = users.role_id
                LEFT JOIN guards_profiles gp ON gp.user_id = users.id
                WHERE roles.name = "Guard"';
        $params = [];
        if ($search) {
            $sql .= ' AND (users.name LIKE :search OR users.email LIKE :search OR gp.badge_number LIKE :search)';
            $params['search'] = "%{$search}%";
        }
        $sql .= ' ORDER BY users.name';
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    public function createGuard(array $data): int
    {
        $this->db->beginTransaction();
        $roleId = $this->roleId('Guard');
        $stmt = $this->db->prepare(
            'INSERT INTO users (role_id, name, email, password_hash, status)
             VALUES (:role_id, :name, :email, :password_hash, "active")'
        );
        $stmt->execute([
            'role_id' => $roleId,
            'name' => $data['name'],
            'email' => $data['email'],
            'password_hash' => password_hash($data['password'], PASSWORD_BCRYPT),
        ]);
        $userId = (int) $this->db->lastInsertId();

        $profile = $this->db->prepare(
            'INSERT INTO guards_profiles (user_id, phone, badge_number, certification, emergency_contact)
             VALUES (:user_id, :phone, :badge_number, :certification, :emergency_contact)'
        );
        $profile->execute([
            'user_id' => $userId,
            'phone' => $data['phone'] ?? null,
            'badge_number' => $data['badge_number'] ?? null,
            'certification' => $data['certification'] ?? null,
            'emergency_contact' => $data['emergency_contact'] ?? null,
        ]);

        $this->db->commit();
        return $userId;
    }

    public function deactivateGuard(int $id): void
    {
        $stmt = $this->db->prepare(
            'UPDATE users
             JOIN roles ON roles.id = users.role_id
             SET users.status = "inactive"
             WHERE users.id = :id AND roles.name = "Guard"'
        );
        $stmt->execute(['id' => $id]);
    }

    private function roleId(string $role): int
    {
        $stmt = $this->db->prepare('SELECT id FROM roles WHERE name = :role LIMIT 1');
        $stmt->execute(['role' => $role]);
        return (int) $stmt->fetchColumn();
    }
}
