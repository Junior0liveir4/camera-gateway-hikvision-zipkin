# Camera Hikvision Gateway
Camera Gateway for Hikvision with Zipkin Tracing and gRPC Support

This project implements a camera gateway service for Hikvision IP cameras, designed to run in a Kubernetes cluster. It supports real-time video stream configuration, PTZ control, and image capture, with OpenCensus Zipkin integration for distributed tracing.

🔧 Features:
- Integration with Hikvision IP cameras via RTSP/HTTP
- Protobuf-based gRPC interface for configuration and control
- Frame publishing via AMQP (RabbitMQ)
- Distributed tracing with Zipkin
- Kubernetes-ready with ConfigMap-based configuration

📦 Technologies:
- Python 3
- OpenCV
- OpenCensus + Zipkin
- gRPC (is-wire)
- Kubernetes
- RabbitMQ (AMQP)

🚀 Use case:
This gateway can be used in computer vision pipelines, surveillance platforms, and any environment that requires PTZ-capable real-time video integration with tracing observability.

## 📷 Project Specifications

In this project, two cameras are using the gateway:

| **Name**                      | **Camera ID** | **IP**         | **Environment** |
|------------------------------|---------------|----------------|-----------------|
| Camera-Gateway-HikVision-1   | 5             | 10.10.10.5     | lab-internal    |

## How to Run the Camera Gateway

### ✅ Prerequisites

- Kubernetes cluster (minikube, kind, GKE etc.)
- Docker
- RabbitMQ (ex: `amqp://rabbitmq.default`)
- Zipkin (ex: `http://zipkin.default.svc.cluster.local:9411`)
- Camera IP Hikvision RTSP/HTTP

## Topic:
CameraGateway.<camera_id>.Frame
