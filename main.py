import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    vgg_tag = 'vgg16'
    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)

    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    return (tf.get_default_graph().get_tensor_by_name(vgg_input_tensor_name),
            tf.get_default_graph().get_tensor_by_name(vgg_keep_prob_tensor_name),
            tf.get_default_graph().get_tensor_by_name(vgg_layer3_out_tensor_name),
            tf.get_default_graph().get_tensor_by_name(vgg_layer4_out_tensor_name),
            tf.get_default_graph().get_tensor_by_name(vgg_layer7_out_tensor_name))
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer7_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer3_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    layer = tf.layers.conv2d(vgg_layer7_out, num_classes, 1, strides=(1, 1))
    layer = tf.layers.conv2d_transpose(layer, 512, 4, strides=(2, 2),
                                       padding='SAME')
    layer = tf.add(layer, vgg_layer4_out)
    layer = tf.layers.conv2d_transpose(layer, 256, 4, strides=(2, 2),
                                       padding='SAME')
    layer = tf.add(layer, vgg_layer3_out)
    layer = tf.layers.conv2d_transpose(layer, num_classes, 16, strides=(8, 8),
                                       padding='SAME')
    return layer
tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    cross_entropy_loss = tf.nn.softmax_cross_entropy_with_logits(
        logits=logits, labels=correct_label)
    cost = tf.reduce_mean(cross_entropy_loss)
    optimizer = tf.train.AdamOptimizer().minimize(cost)
    return logits, optimizer, cost
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    sess.run(tf.global_variables_initializer())
    for e in range(epochs):
        for i, (x, y) in enumerate(get_batches_fn(batch_size)):
            feed = {input_image: x,
                    correct_label: y,
                    keep_prob: 0.5}
            loss, _ = sess.run([cross_entropy_loss, train_op], feed_dict=feed)
            print("epoch: {} iter: {} loss: {}".format(e, i, loss))

    pass
tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        output = tf.placeholder(tf.float32, [None, 160, 576, num_classes])

        image_input, keep_prob, layer3_out, layer4_out, layer7_out = load_vgg(sess, vgg_path)
        last_layer = layers(layer3_out, layer4_out, layer7_out, num_classes)
        logits, optimizer, cost = optimize(last_layer, output, 0.1, num_classes)

        train_nn(sess, 20, 32, get_batches_fn, optimizer, cost,
                 image_input, output, keep_prob, None)

        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape,
                                      logits, keep_prob, image_input)


if __name__ == '__main__':
    run()
