<?php
declare(strict_types=1);

require_once __DIR__ . '/../models/Dashboard.php';

final class DashboardController
{
    public function summary(): void
    {
        $user = require_auth();
        json_response(['data' => (new Dashboard())->summary($user)]);
    }
}
