<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/Report.php';

final class ReportController
{
    public function daily(): void
    {
        $user = require_auth(['Admin', 'Supervisor', 'Client']);
        $date = isset($_GET['date']) ? clean_string($_GET['date'], 20) : date('Y-m-d');
        $report = (new Report())->daily($user, $date);

        if (($_GET['format'] ?? '') === 'pdf') {
            header('Content-Type: text/html; charset=utf-8');
            echo '<!doctype html><title>Patrol Pro Daily Report</title><style>body{font-family:Arial;padding:32px}h1{color:#be185d}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}</style>';
            echo '<h1>Patrol Pro Daily Report</h1><p>Date: ' . htmlspecialchars($date) . '</p><script>window.print()</script>';
            echo '<h2>Patrol Summary</h2><pre>' . htmlspecialchars(json_encode($report, JSON_PRETTY_PRINT)) . '</pre>';
            exit;
        }

        json_response(['data' => $report]);
    }
}
