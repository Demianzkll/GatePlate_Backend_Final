# Raspberry Pi 5 RTSP USB Camera Streamer

A lightweight, Docker-based setup to stream a USB webcam over RTSP and WebRTC using MediaMTX and FFmpeg on a Raspberry Pi 5.

## Prerequisites
* Raspberry Pi 5 with Raspberry Pi OS (or compatible Linux distro)
* USB Webcam connected (typically recognized as `/dev/video0`)
* [Docker and Docker Compose](https://docs.docker.com/engine/install/) installed

## Setup Instructions

### 1. Create a project directory
```bash
docker compose up -d
```

Viewing the Stream:
In browser:
[http://raspberrypi.local:8889/cam](http://raspberrypi.local:8889/cam)

In bash on Linux:
ffplay -rtsp_transport tcp rtsp://raspberrypi.local:8554/cam