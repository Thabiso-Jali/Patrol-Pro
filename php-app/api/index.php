<?php
declare(strict_types=1);

require_once __DIR__ . '/helpers.php';
require_once __DIR__ . '/../auth/session.php';
require_once __DIR__ . '/../controllers/AuthController.php';
require_once __DIR__ . '/../controllers/DashboardController.php';
require_once __DIR__ . '/../controllers/GuardController.php';
require_once __DIR__ . '/../controllers/PatrolController.php';
require_once __DIR__ . '/../controllers/IncidentController.php';
require_once __DIR__ . '/../controllers/ShiftController.php';
require_once __DIR__ . '/../controllers/ReportController.php';
require_once __DIR__ . '/../controllers/NotificationController.php';

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$path = preg_replace('#^/api#', '', $path) ?: '/';

try {
    $routes = [
        'POST /login' => [AuthController::class, 'login'],
        'POST /logout' => [AuthController::class, 'logout'],
        'GET /me' => [AuthController::class, 'me'],
        'GET /dashboard' => [DashboardController::class, 'summary'],
        'GET /guards' => [GuardController::class, 'index'],
        'POST /guards' => [GuardController::class, 'store'],
        'DELETE /guards' => [GuardController::class, 'destroy'],
        'GET /patrols' => [PatrolController::class, 'index'],
        'POST /patrols' => [PatrolController::class, 'store'],
        'DELETE /patrols' => [PatrolController::class, 'destroy'],
        'POST /patrols/checkpoint' => [PatrolController::class, 'completeCheckpoint'],
        'GET /incidents' => [IncidentController::class, 'index'],
        'POST /incidents' => [IncidentController::class, 'store'],
        'DELETE /incidents' => [IncidentController::class, 'destroy'],
        'GET /shifts' => [ShiftController::class, 'index'],
        'POST /shifts' => [ShiftController::class, 'store'],
        'POST /shifts/start' => [ShiftController::class, 'start'],
        'POST /shifts/clock-out' => [ShiftController::class, 'clockOut'],
        'DELETE /shifts' => [ShiftController::class, 'destroy'],
        'GET /reports' => [ReportController::class, 'daily'],
        'GET /notifications' => [NotificationController::class, 'index'],
        'POST /notifications/read' => [NotificationController::class, 'markRead'],
    ];

    $key = "{$method} {$path}";
    if (!isset($routes[$key])) {
        json_response(['error' => 'Endpoint not found'], 404);
    }

    [$class, $action] = $routes[$key];
    (new $class())->$action();
} catch (Throwable $e) {
    $config = require __DIR__ . '/../config/config.php';
    $message = $config['debug'] ? $e->getMessage() : 'Unexpected server error';
    json_response(['error' => $message], 500);
}
