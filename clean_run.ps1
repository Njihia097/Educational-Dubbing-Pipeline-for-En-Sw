# Run => .\clean_run.ps1
/**
 * This script cleans up old Docker containers and volumes related to the project,
 * then rebuilds and starts the containers afresh.
 */

Write-Host "🧹 Cleaning up old Docker containers and volumes..."
docker-compose down -v --remove-orphans

# Force-remove any leftover project containers by name prefix
$containers = docker ps -a --format "{{.Names}}" | Select-String -Pattern "edu_"
foreach ($container in $containers) {
    Write-Host "Removing container $($container.Line)..."
    docker rm -f $($container.Line)
}

Write-Host "Rebuilding and starting containers..."
docker-compose up -d --build

Write-Host "All services rebuilt successfully!"
docker ps
