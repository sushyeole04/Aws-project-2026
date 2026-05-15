# 2️⃣ Scalable Web App with NLB and Auto Scaling

## 🎯 Purpose
To build a system that can handle very high-performance and ultra low-latency traffic, ideal for applications where speed and connection stability are critical.

## 🧰 AWS Services Used
- **Amazon EC2** → Hosts the application servers
- **Network Load Balancer** → Handles high-speed traffic at Layer 4 (TCP/UDP)
- **Auto Scaling Group** → Dynamically scales EC2 instances

## 🏗️ Architecture Overview
7

## 🔄 Working Flow
1. User sends request (TCP/UDP traffic)
2. Request hits Network Load Balancer (NLB)
3. NLB forwards traffic directly to EC2 instances
4. Auto Scaling Group (ASG):
   - Adds instances when load increases
   - Removes instances when load decreases
5. NLB maintains static IP + ultra-low latency routing

## ⚙️ Key Features
- **Ultra Low Latency** → Designed for high-speed performance
- **High Throughput** → Handles millions of requests per second
- **Static IP Support** → Useful for whitelisting
- **Layer 4 Load Balancing** → Works with TCP/UDP

## ⚖️ NLB vs ALB (Quick Difference)
| Feature | NLB | ALB |
|---------|-----|-----|
| **Layer** | Layer 4 (TCP/UDP) | Layer 7 (HTTP/HTTPS) |
| **Speed** | Very Fast ⚡ | Moderate |
| **Routing** | Basic | Advanced (path-based, host-based) |
| **Use Case** | Gaming, IoT, real-time apps | Web apps, APIs |

## 🚀 Instance Configuration
- Recommended: `t3.micro` for better performance

## 🔐 Security Consideration
- Allow only required ports (e.g., TCP 80 or 443)
- Restrict EC2 access to NLB traffic where possible

## 💡 Real-World Use Cases
- Online gaming servers 🎮
- Financial trading systems 💹
- Real-time messaging apps
- IoT backends
