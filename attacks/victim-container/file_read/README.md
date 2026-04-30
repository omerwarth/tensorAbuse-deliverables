# Tensorabuse ARM

A Docker-based project for ARM64, demonstrating TensorFlow model execution with listener and victim containers. This project shows how TensorFlow's debug operations can be exploited to exfiltrate data.

## Structure

```
tensorabuse-arm/
├── listener-container/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── listener.py          # Socket listener on port 9000
├── victim-container/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── build_model.py       # Creates malicious TensorFlow model
│   └── run_victim.py        # Executes the model (triggers data exfil)
└── docker-compose.yml       # Multi-container orchestration
```

## How It Works

1. **Listener Container**: Runs a simple TCP socket server on port 9000 (IP: 10.10.0.6)
2. **Victim Container**: 
   - Creates a secret file (`/tmp/secret.txt`)
   - Builds a TensorFlow model with malicious operations
   - Uses `tf.raw_ops.ReadFile` to read the secret
   - Uses `tf.raw_ops.DebugIdentityV3` with gRPC to send data to listener
   - Executes the model, triggering the data exfiltration

## Requirements

- Docker (with ARM64 support)
- Docker Compose
- Linux Ubuntu VM (tested on ARM64)

## Setup

### 1. Clone or copy the project files

```bash
# If you have the files, navigate to the project directory
cd tensorabuse-arm
```

### 2. Verify file structure

```bash
ls -R
```

You should see:
- `docker-compose.yml`
- `listener-container/` with Dockerfile and listener.py
- `victim-container/` with Dockerfile, build_model.py, and run_victim.py

## Usage

### Build and run the containers

```bash
docker-compose up --build
```

This will:
1. Build both Docker images (may take 5-10 minutes on first build due to TensorFlow)
2. Start the listener container
3. Start the victim container
4. The victim will build the model, execute it, and exfiltrate the secret
5. The listener will receive and display the secret message

### Run in detached mode

```bash
docker-compose up -d --build
```

### View logs

```bash
# All containers
docker-compose logs -f

# Listener only
docker-compose logs -f listener

# Victim only
docker-compose logs -f victim
```

### Stop containers

```bash
docker-compose down
```

### Clean up (remove images)

```bash
docker-compose down --rmi all -v
```

## Expected Output

**Listener Container:**
```
Listening on 0.0.0.0:9000
Connection from: ('10.10.0.x', xxxxx)
Received: THIS_IS_A_SECRET_MESSAGE
```

**Victim Container:**
```
Malicious model saved
Loading malicious model
Triggering inference
Model output: ...
```

## Network Configuration

The docker-compose.yml creates a custom bridge network:
- Network: `10.10.0.0/24`
- Listener static IP: `10.10.0.6:9000`
- Victim: Dynamic IP in the same subnet

## Troubleshooting

### TensorFlow build takes too long
ARM64 builds can be slow. First build may take 10-15 minutes.

### Connection refused
Make sure the listener container is fully started before the victim executes. The `depends_on` directive should handle this.

### Port already in use
If port 9000 is already in use on your host:
```bash
# Check what's using port 9000
sudo lsof -i :9000

# Or change the port in docker-compose.yml
ports:
  - "9001:9000"  # Map host port 9001 to container port 9000
```

### Permission denied
Make sure Docker can be run without sudo:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

## Security Note

This project is for educational purposes only. It demonstrates:
- TensorFlow's `tf.raw_ops.ReadFile` can read arbitrary files
- `tf.raw_ops.DebugIdentityV3` can send data over the network
- Malicious models can exfiltrate sensitive data

**Do not use malicious models in production environments.**

## License

Educational/Research Use Only
