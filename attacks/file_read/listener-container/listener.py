import socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 9000))
server.listen(1)

print("Listening on 0.0.0.0:9000")

conn, addr = server.accept()
print("Connection from:", addr)

# Receive multiple chunks - gRPC sends handshake first, then data
all_data = b""
while len(all_data) < 8192:
    data = conn.recv(4096)
    if not data:
        break
    all_data += data
    
    if b"THIS_IS_A_SECRET_MESSAGE" in all_data:
        break

# Search for the secret in received data
secret_msg = b"THIS_IS_A_SECRET_MESSAGE"
if secret_msg in all_data:
    print("Received:", secret_msg.decode())
else:
    print("Secret not found in received data")

conn.close()
