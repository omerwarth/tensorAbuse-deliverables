import os
import tensorflow as tf

model = tf.saved_model.load("shell_access_model")
infer = model.signatures["serving_default"]
infer(x=tf.constant(1.0))

if os.path.exists("/root/.ssh/authorized_keys"):
	print("SUCCESS: authorized_keys modified")
