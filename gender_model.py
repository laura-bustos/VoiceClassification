import os
import numpy as np
from keras.utils import np_utils
import tensorflow as tf
from tensorflow.contrib.data import Dataset, Iterator
import sys
from train import load_data, build_graph


def train(summary_dir, steps, samples):
    time_steps = 128
    num_classes = 2
    feature_size = 13
    learning_rate = 0.001
    training_steps = steps

    x_train, y_train, x_test, y_test = load_data("gender", samples, int(samples / 5))
    _, counts = np.unique(y_train, return_counts=True)

    y_train = np_utils.to_categorical(y_train)
    y_test = np_utils.to_categorical(y_test)
    x_test = x_test.reshape((-1, time_steps, feature_size))
    y_test = y_test.reshape((-1, num_classes))

    counts_inverse = [samples - i for i in counts]
    normed_weights = [(float(i)/sum(counts_inverse)) for i in counts_inverse]
    print(normed_weights)
    class_weights = tf.constant([normed_weights])
    x, y, loss, accuracy, optimizer, summary_op = build_graph(feature_size, time_steps, num_classes, class_weights, learning_rate)
    train_data = tf.data.Dataset.from_tensor_slices((x_train, y_train))

    with tf.Session() as sess:
        summary_writer = tf.summary.FileWriter(summary_dir, sess.graph)
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()

        for step in range(1, training_steps + 1):
            total_loss = 0.0
            total_accuracy = 0.0
            total_steps = 0
            iterator = Iterator.from_structure(train_data.output_types, train_data.output_shapes)
            next_element = iterator.get_next()
            sess.run(iterator.make_initializer(train_data))
            print("Step: ", step)
            while True:
                try:
                    total_steps += 1
                    x_element, y_element = sess.run(next_element)
                    x_element = x_element.reshape((1, time_steps, feature_size))
                    y_element = y_element.reshape((-1, num_classes))
                    feed_dict = {x: x_element, y: y_element}
                    loss_value, accuracy_value, _ = sess.run([loss, accuracy, optimizer], feed_dict=feed_dict)
                    total_loss += loss_value
                    total_accuracy += accuracy_value
                except tf.errors.OutOfRangeError:
                    break

            if step % 5 == 0:
                feed_dict = {x: x_train, y: y_train}
                _, _, summary = sess.run([loss, accuracy, summary_op], feed_dict=feed_dict)
                summary_writer.add_summary(summary, step)

            print("Loss: ", total_loss / total_steps)
            print("Accuracy: ", total_accuracy / total_steps)
            sys.stdout.flush()

        saver.save(sess, './models/model-gender.ckpt')

        print("\nGender Train Accuracy: ", sess.run(accuracy, feed_dict={x: x_train, y: y_train}))
        print("Gender Test Accuracy: ", sess.run(accuracy, feed_dict={x: x_test, y: y_test}))
