<?php
declare(strict_types=1);

function json_input(): array
{
    $raw = file_get_contents('php://input') ?: '';
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : [];
}

function json_response(array $payload, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($payload, JSON_THROW_ON_ERROR);
    exit;
}

function clean_string(mixed $value, int $max = 255): string
{
    $value = trim((string) $value);
    $value = mb_substr($value, 0, $max);
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function require_fields(array $data, array $fields): void
{
    foreach ($fields as $field) {
        if (!isset($data[$field]) || trim((string) $data[$field]) === '') {
            json_response(['error' => "Missing required field: {$field}"], 422);
        }
    }
}
