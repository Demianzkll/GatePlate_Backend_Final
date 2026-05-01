@echo off
start "MediaMTX Server" cmd /k ".\mediamtx.exe"
timeout /t 2
start "FFmpeg Cam1" cmd /k ".\ffmpeg -re -stream_loop -1 -i videos\video1.mp4 -c copy -f rtsp rtsp://localhost:8554/cam1"
start "FFmpeg Cam2" cmd /k ".\ffmpeg -re -stream_loop -1 -i videos\video2.mp4 -c copy -f rtsp rtsp://localhost:8554/cam2"
start "FFmpeg Cam3" cmd /k ".\ffmpeg -re -stream_loop -1 -i videos\video3.mp4 -c copy -f rtsp rtsp://localhost:8554/cam3"
start "FFmpeg Cam4" cmd /k ".\ffmpeg -re -stream_loop -1 -i videos\video4.mp4 -c copy -f rtsp rtsp://localhost:8554/cam4"
echo Система готова! Транслюються 4 камери (/cam1, /cam2, /cam3, /cam4)