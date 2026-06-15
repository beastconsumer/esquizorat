@echo off
cd /d "C:\Users\Pichau\Desktop\Project - Copia (3)"
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker ps -a
