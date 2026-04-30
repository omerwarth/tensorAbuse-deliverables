import tensorflow as tf

print("Loading malicious model")
model = tf.saved_model.load("malicious_saved_model")
infer = model.signatures["serving_default"]

print("Triggering inference")
result = infer(x=tf.constant(3.0))

print("Model output: ", result)
