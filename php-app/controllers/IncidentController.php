<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/Incident.php';
require_once __DIR__ . '/../models/AuditLog.php';
require_once __DIR__ . '/../models/Notification.php';

final class IncidentController
{
    public function index(): void
    {
        $user = require_auth();
        $filters = [
            'status' => isset($_GET['status']) ? clean_string($_GET['status'], 40) : null,
            'date' => isset($_GET['date']) ? clean_string($_GET['date'], 20) : null,
        ];
        json_response(['data' => (new Incident())->list($user, $filters)]);
    }

    public function store(): void
    {
        $user = require_auth(['Guard', 'Admin', 'Supervisor']);
        $data = $_POST ?: json_input();
        require_fields($data, ['client_id', 'category', 'title']);

        $evidencePath = $this->storeEvidence();
        $id = (new Incident())->create([
            'client_id' => (int) $data['client_id'],
            'route_id' => !empty($data['route_id']) ? (int) $data['route_id'] : null,
            'category' => clean_string($data['category'], 80),
            'severity' => clean_string($data['severity'] ?? 'medium', 20),
            'title' => clean_string($data['title'], 180),
            'notes' => clean_string($data['notes'] ?? '', 3000),
            'evidence_path' => $evidencePath,
            'latitude' => $data['latitude'] ?? null,
            'longitude' => $data['longitude'] ?? null,
        ], (int) $user['id']);

        (new Notification())->create(null, 'New incident reported', clean_string($data['title'], 180), 'incident');
        (new AuditLog())->record((int) $user['id'], 'incident.create', 'incident', $id);
        json_response(['id' => $id], 201);
    }

    public function destroy(): void
    {
        $user = require_auth(['Admin', 'Supervisor']);
        $id = (int) ($_GET['id'] ?? 0);
        if ($id <= 0) {
            json_response(['error' => 'Incident id is required'], 422);
        }
        (new Incident())->delete($id);
        (new AuditLog())->record((int) $user['id'], 'incident.delete', 'incident', $id);
        json_response(['ok' => true]);
    }

    private function storeEvidence(): ?string
    {
        if (empty($_FILES['evidence']) || $_FILES['evidence']['error'] !== UPLOAD_ERR_OK) {
            return null;
        }
        $allowed = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'];
        $mime = mime_content_type($_FILES['evidence']['tmp_name']);
        $config = require __DIR__ . '/../config/config.php';
        $maxBytes = (int) $config['max_upload_mb'] * 1024 * 1024;
        if (!isset($allowed[$mime]) || $_FILES['evidence']['size'] > $maxBytes) {
            json_response(['error' => "Evidence must be a JPG, PNG, or WebP image under {$config['max_upload_mb']}MB"], 422);
        }
        $name = bin2hex(random_bytes(16)) . '.' . $allowed[$mime];
        $target = rtrim($config['upload_dir'], '/') . '/' . $name;
        if (!is_dir($config['upload_dir']) && !mkdir($config['upload_dir'], 0755, true)) {
            json_response(['error' => 'Unable to prepare evidence storage'], 500);
        }
        if (!move_uploaded_file($_FILES['evidence']['tmp_name'], $target)) {
            json_response(['error' => 'Unable to store evidence upload'], 500);
        }
        return '/uploads/incidents/' . $name;
    }
}
