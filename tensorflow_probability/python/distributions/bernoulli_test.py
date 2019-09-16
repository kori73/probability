# Copyright 2018 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Tests for the Bernoulli distribution."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Dependency imports

import numpy as np
from scipy import special as sp_special
import tensorflow.compat.v1 as tf1
import tensorflow.compat.v2 as tf
import tensorflow_probability as tfp
from tensorflow_probability.python import distributions as tfd
from tensorflow_probability.python.internal import tensorshape_util
from tensorflow_probability.python.internal import test_case
from tensorflow_probability.python.internal import test_util as tfp_test_util

from tensorflow.python.framework import test_util  # pylint: disable=g-direct-tensorflow-import


def make_bernoulli(batch_shape, dtype=tf.int32):
  p = np.random.uniform(size=list(batch_shape))
  p = tf.constant(p, dtype=tf.float32)
  return tfd.Bernoulli(probs=p, dtype=dtype)


def entropy(p):
  q = 1. - p
  return -q * np.log(q) - p * np.log(p)


@test_util.run_all_in_graph_and_eager_modes
class BernoulliTest(test_case.TestCase):

  def testP(self):
    p = [0.2, 0.4]
    dist = tfd.Bernoulli(probs=p)
    self.assertAllClose(p, self.evaluate(dist.probs))

  def testLogits(self):
    logits = [-42., 42.]
    dist = tfd.Bernoulli(logits=logits)
    self.assertAllClose(logits, self.evaluate(dist.logits))
    self.assertAllClose(sp_special.expit(logits), self.evaluate(dist.probs))

    p = [0.01, 0.99, 0.42]
    dist = tfd.Bernoulli(probs=p)
    self.assertAllClose(sp_special.logit(p), self.evaluate(dist.logits))

  def testInvalidP(self):
    invalid_ps = [1.01, 2.]
    for p in invalid_ps:
      with self.assertRaisesOpError('probs has components greater than 1'):
        dist = tfd.Bernoulli(probs=p, validate_args=True)
        self.evaluate(dist.probs_parameter())

    invalid_ps = [-0.01, -3.]
    for p in invalid_ps:
      with self.assertRaisesOpError('x >= 0 did not hold'):
        dist = tfd.Bernoulli(probs=p, validate_args=True)
        self.evaluate(dist.probs_parameter())

    valid_ps = [0.0, 0.5, 1.0]
    for p in valid_ps:
      dist = tfd.Bernoulli(probs=p)
      self.assertEqual(p, self.evaluate(dist.probs))  # Should not fail

  def testShapes(self):
    for batch_shape in ([], [1], [2, 3, 4]):
      dist = make_bernoulli(batch_shape)
      self.assertAllEqual(batch_shape,
                          tensorshape_util.as_list(dist.batch_shape))
      self.assertAllEqual(batch_shape, self.evaluate(dist.batch_shape_tensor()))
      self.assertAllEqual([], tensorshape_util.as_list(dist.event_shape))
      self.assertAllEqual([], self.evaluate(dist.event_shape_tensor()))

  def testDtype(self):
    dist = make_bernoulli([])
    self.assertEqual(dist.dtype, tf.int32)
    self.assertEqual(dist.dtype, dist.sample(5).dtype)
    self.assertEqual(dist.dtype, dist.mode().dtype)
    self.assertEqual(dist.probs.dtype, dist.mean().dtype)
    self.assertEqual(dist.probs.dtype, dist.variance().dtype)
    self.assertEqual(dist.probs.dtype, dist.stddev().dtype)
    self.assertEqual(dist.probs.dtype, dist.entropy().dtype)
    self.assertEqual(dist.probs.dtype, dist.prob(0).dtype)
    self.assertEqual(dist.probs.dtype, dist.prob(0.5).dtype)
    self.assertEqual(dist.probs.dtype, dist.log_prob(0).dtype)
    self.assertEqual(dist.probs.dtype, dist.log_prob(0.5).dtype)

    dist64 = make_bernoulli([], tf.int64)
    self.assertEqual(dist64.dtype, tf.int64)
    self.assertEqual(dist64.dtype, dist64.sample(5).dtype)
    self.assertEqual(dist64.dtype, dist64.mode().dtype)

  def testFloatMode(self):
    dist = tfd.Bernoulli(probs=.6, dtype=tf.float32)
    self.assertEqual(np.float32(1), self.evaluate(dist.mode()))

  def _testPmf(self, **kwargs):
    dist = tfd.Bernoulli(**kwargs)
    # pylint: disable=bad-continuation
    xs = [
        0,
        [1],
        [1, 0],
        [[1, 0]],
        [[1, 0], [1, 1]],
    ]
    expected_pmfs = [
        [[0.8, 0.6], [0.7, 0.4]],
        [[0.2, 0.4], [0.3, 0.6]],
        [[0.2, 0.6], [0.3, 0.4]],
        [[0.2, 0.6], [0.3, 0.4]],
        [[0.2, 0.6], [0.3, 0.6]],
    ]
    # pylint: enable=bad-continuation

    for x, expected_pmf in zip(xs, expected_pmfs):
      self.assertAllClose(self.evaluate(dist.prob(x)), expected_pmf)
      self.assertAllClose(self.evaluate(dist.log_prob(x)), np.log(expected_pmf))

  def testPmfCorrectBroadcastDynamicShape(self):
    p = tf1.placeholder_with_default([0.2, 0.3, 0.4], shape=None)
    dist = tfd.Bernoulli(probs=p)
    event1 = [1, 0, 1]
    event2 = [[1, 0, 1]]
    self.assertAllClose(
        [0.2, 0.7, 0.4], self.evaluate(dist.prob(event1)))
    self.assertAllClose(
        [[0.2, 0.7, 0.4]], self.evaluate(dist.prob(event2)))

  def testPmfInvalid(self):
    p = [0.1, 0.2, 0.7]
    dist = tfd.Bernoulli(probs=p, validate_args=True)
    with self.assertRaisesOpError('must be non-negative.'):
      self.evaluate(dist.prob([1, 1, -1]))
    with self.assertRaisesOpError('Elements cannot exceed 1.'):
      self.evaluate(dist.prob([2, 0, 1]))

  def testPmfWithP(self):
    p = [[0.2, 0.4], [0.3, 0.6]]
    self._testPmf(probs=p)
    self._testPmf(logits=sp_special.logit(p))

  def testPmfWithFloatArgReturnsXEntropy(self):
    p = [[0.2], [0.4], [0.3], [0.6]]
    samps = [0, 0.1, 0.8]
    self.assertAllClose(
        np.float32(samps) * np.log(np.float32(p)) +
        (1 - np.float32(samps)) * np.log(1 - np.float32(p)),
        self.evaluate(
            tfd.Bernoulli(probs=p, validate_args=False).log_prob(samps)))

  def testBroadcasting(self):
    probs = lambda p: tf1.placeholder_with_default(p, shape=None)
    dist = lambda p: tfd.Bernoulli(probs=probs(p))
    self.assertAllClose(np.log(0.5), self.evaluate(dist(0.5).log_prob(1)))
    self.assertAllClose(
        np.log([0.5, 0.5, 0.5]), self.evaluate(dist(0.5).log_prob([1, 1, 1])))
    self.assertAllClose(np.log([0.5, 0.5, 0.5]),
                        self.evaluate(dist([0.5, 0.5, 0.5]).log_prob(1)))

  def testPmfShapes(self):
    probs = lambda p: tf1.placeholder_with_default(p, shape=None)
    dist = lambda p: tfd.Bernoulli(probs=probs(p))
    self.assertEqual(
        2, len(self.evaluate(dist([[0.5], [0.5]]).log_prob(1)).shape))

    dist = tfd.Bernoulli(probs=0.5)
    self.assertEqual(2, len(self.evaluate(dist.log_prob([[1], [1]])).shape))

    dist = tfd.Bernoulli(probs=0.5)
    self.assertEqual((), dist.log_prob(1).shape)
    self.assertEqual((1), dist.log_prob([1]).shape)
    self.assertEqual((2, 1), dist.log_prob([[1], [1]]).shape)

    dist = tfd.Bernoulli(probs=[[0.5], [0.5]])
    self.assertEqual((2, 1), dist.log_prob(1).shape)

  def testBoundaryConditions(self):
    dist = tfd.Bernoulli(probs=1.0)
    self.assertAllClose(np.nan, self.evaluate(dist.log_prob(0)))
    self.assertAllClose([np.nan], [self.evaluate(dist.log_prob(1))])

  def testEntropyNoBatch(self):
    p = 0.2
    dist = tfd.Bernoulli(probs=p)
    self.assertAllClose(self.evaluate(dist.entropy()), entropy(p))

  def testEntropyWithBatch(self):
    p = [[0.1, 0.7], [0.2, 0.6]]
    dist = tfd.Bernoulli(probs=p, validate_args=False)
    self.assertAllClose(
        self.evaluate(dist.entropy()),
        [[entropy(0.1), entropy(0.7)], [entropy(0.2),
                                        entropy(0.6)]])

  def testSampleN(self):
    p = [0.2, 0.6]
    dist = tfd.Bernoulli(probs=p)
    n = 100000
    samples = dist.sample(n)
    tensorshape_util.set_shape(samples, [n, 2])
    self.assertEqual(samples.dtype, tf.int32)
    sample_values = self.evaluate(samples)
    self.assertTrue(np.all(sample_values >= 0))
    self.assertTrue(np.all(sample_values <= 1))
    # Note that the standard error for the sample mean is ~ sqrt(p * (1 - p) /
    # n). This means that the tolerance is very sensitive to the value of p
    # as well as n.
    self.assertAllClose(p, np.mean(sample_values, axis=0), atol=1e-2)
    self.assertEqual(set([0, 1]), set(sample_values.flatten()))
    # In this test we're just interested in verifying there isn't a crash
    # owing to mismatched types. b/30940152
    dist = tfd.Bernoulli(np.log([.2, .4]))
    x = dist.sample(1, seed=tfp_test_util.test_seed())
    self.assertAllEqual((1, 2), tensorshape_util.as_list(x.shape))

  def testNotReparameterized(self):
    p = tf.constant([0.2, 0.6])
    _, grad_p = tfp.math.value_and_gradient(
        lambda x: tfd.Bernoulli(probs=x).sample(100), p)
    self.assertIsNone(grad_p)

  def testSampleDeterministicScalarVsVector(self):
    p = [0.2, 0.6]
    dist = tfd.Bernoulli(probs=p)
    n = 1000
    def _maybe_seed():
      if tf.executing_eagerly():
        tf1.set_random_seed(42)
        return None
      return 42
    self.assertAllEqual(
        self.evaluate(dist.sample(n, _maybe_seed())),
        self.evaluate(dist.sample([n], _maybe_seed())))
    n = tf1.placeholder_with_default(np.int32(1000), shape=None)
    sample1 = dist.sample(n, _maybe_seed())
    sample2 = dist.sample([n], _maybe_seed())
    sample1, sample2 = self.evaluate([sample1, sample2])
    self.assertAllEqual(sample1, sample2)

  def testMean(self):
    p = np.array([[0.2, 0.7], [0.5, 0.4]], dtype=np.float32)
    dist = tfd.Bernoulli(probs=p)
    self.assertAllEqual(self.evaluate(dist.mean()), p)

  def testVarianceAndStd(self):
    var = lambda p: p * (1. - p)
    p = [[0.2, 0.7], [0.5, 0.4]]
    dist = tfd.Bernoulli(probs=p)
    self.assertAllClose(
        self.evaluate(dist.variance()),
        np.array([[var(0.2), var(0.7)], [var(0.5), var(0.4)]],
                 dtype=np.float32))
    self.assertAllClose(
        self.evaluate(dist.stddev()),
        np.array([[np.sqrt(var(0.2)), np.sqrt(var(0.7))],
                  [np.sqrt(var(0.5)), np.sqrt(var(0.4))]],
                 dtype=np.float32))

  def testBernoulliBernoulliKL(self):
    batch_size = 6
    a_p = np.array([0.6] * batch_size, dtype=np.float32)
    b_p = np.array([0.4] * batch_size, dtype=np.float32)

    a = tfd.Bernoulli(probs=a_p)
    b = tfd.Bernoulli(probs=b_p)

    kl = tfd.kl_divergence(a, b)
    kl_val = self.evaluate(kl)

    kl_expected = (a_p * np.log(a_p / b_p) + (1. - a_p) * np.log(
        (1. - a_p) / (1. - b_p)))

    self.assertEqual(kl.shape, (batch_size,))
    self.assertAllClose(kl_val, kl_expected)

  def testParamTensorFromLogits(self):
    x = tf.constant([-1., 0.5, 1.])
    d = tfd.Bernoulli(logits=x, validate_args=True)
    logit = lambda x: tf.math.log(x) - tf.math.log1p(-x)
    self.assertAllClose(
        *self.evaluate([logit(d.prob(1.)), d.logits_parameter()]),
        atol=0, rtol=1e-4)
    self.assertAllClose(
        *self.evaluate([d.prob(1.), d.probs_parameter()]),
        atol=0, rtol=1e-4)

  def testParamTensorFromProbs(self):
    x = tf.constant([0.1, 0.5, 0.4])
    d = tfd.Bernoulli(probs=x, validate_args=True)
    logit = lambda x: tf.math.log(x) - tf.math.log1p(-x)
    self.assertAllClose(
        *self.evaluate([logit(d.prob(1.)), d.logits_parameter()]),
        atol=0, rtol=1e-4)
    self.assertAllClose(
        *self.evaluate([d.prob(1.), d.probs_parameter()]),
        atol=0, rtol=1e-4)


class _MakeSlicer(object):

  def __getitem__(self, slices):
    return lambda x: x[slices]

make_slicer = _MakeSlicer()


@test_util.run_all_in_graph_and_eager_modes
class BernoulliSlicingTest(test_case.TestCase):

  def testScalarSlice(self):
    logits = self.evaluate(tf.random.normal([]))
    dist = tfd.Bernoulli(logits=logits)
    self.assertAllEqual([], dist.batch_shape)
    self.assertAllEqual([1], dist[tf.newaxis].batch_shape)
    self.assertAllEqual([], dist[...].batch_shape)
    self.assertAllEqual([1, 1], dist[tf.newaxis, ..., tf.newaxis].batch_shape)

  def testSlice(self):
    logits = self.evaluate(tf.random.normal([20, 3, 1, 5]))
    dist = tfd.Bernoulli(logits=logits)
    batch_shape = tensorshape_util.as_list(dist.batch_shape)
    dist_noshape = tfd.Bernoulli(
        logits=tf1.placeholder_with_default(logits, shape=None))

    def check(*slicers):
      for ds, assert_static_shape in (dist, True), (dist_noshape, False):
        bs = batch_shape
        prob = self.evaluate(dist.prob(0))
        for slicer in slicers:
          ds = slicer(ds)
          bs = slicer(np.zeros(bs)).shape
          prob = slicer(prob)
          if assert_static_shape or tf.executing_eagerly():
            self.assertAllEqual(bs, ds.batch_shape)
          else:
            self.assertIsNone(tensorshape_util.rank(ds.batch_shape))
          self.assertAllEqual(bs, self.evaluate(ds.batch_shape_tensor()))
          self.assertAllClose(prob, self.evaluate(ds.prob(0)))

    check(make_slicer[3])
    check(make_slicer[tf.newaxis])
    check(make_slicer[3::7])
    check(make_slicer[:, :2])
    check(make_slicer[tf.newaxis, :, ..., 0, :2])
    check(make_slicer[tf.newaxis, :, ..., 3:, tf.newaxis])
    check(make_slicer[..., tf.newaxis, 3:, tf.newaxis])
    check(make_slicer[..., tf.newaxis, -3:, tf.newaxis])
    check(make_slicer[tf.newaxis, :-3, tf.newaxis, ...])
    def halfway(x):
      if isinstance(x, tfd.Bernoulli):
        return x.batch_shape_tensor()[0] // 2
      return x.shape[0] // 2
    check(lambda x: x[halfway(x)])
    check(lambda x: x[:halfway(x)])
    check(lambda x: x[halfway(x):])
    check(make_slicer[:-3, tf.newaxis], make_slicer[..., 0, :2],
          make_slicer[::2])
    if tf.executing_eagerly(): return
    with self.assertRaisesRegexp((ValueError, tf.errors.InvalidArgumentError),
                                 'Index out of range.*input has only 4 dims'):
      check(make_slicer[19, tf.newaxis, 2, ..., :, 0, 4])
    with self.assertRaisesRegexp((ValueError, tf.errors.InvalidArgumentError),
                                 'slice index.*out of bounds'):
      check(make_slicer[..., 2, :])  # ...,1,5 -> 2 is oob.

  def testSliceSequencePreservesOrigVarGradLinkage(self):
    logits = tf.Variable(tf.random.normal([20, 3, 1, 5]))
    self.evaluate(logits.initializer)
    dist = tfd.Bernoulli(logits=logits)
    for slicer in [make_slicer[:5], make_slicer[..., -1], make_slicer[:, 1::2]]:
      with tf.GradientTape() as tape:
        dist = slicer(dist)
        lp = dist.log_prob(0)
      dlpdlogits = tape.gradient(lp, logits)
      self.assertIsNotNone(dlpdlogits)
      self.assertGreater(
          self.evaluate(tf.reduce_sum(tf.abs(dlpdlogits))), 0)

  def testSliceThenCopyPreservesOrigVarGradLinkage(self):
    logits = tf.Variable(tf.random.normal([20, 3, 1, 5]))
    self.evaluate(logits.initializer)
    dist = tfd.Bernoulli(logits=logits)
    dist = dist[:5]
    with tf.GradientTape() as tape:
      dist = dist.copy(name='bern2')
      lp = dist.log_prob(0)
    dlpdlogits = tape.gradient(lp, logits)
    self.assertIn('bern2', dist.name)
    self.assertIsNotNone(dlpdlogits)
    self.assertGreater(
        self.evaluate(tf.reduce_sum(tf.abs(dlpdlogits))), 0)
    with tf.GradientTape() as tape:
      dist = dist[:3]
      lp = dist.log_prob(0)
    dlpdlogits = tape.gradient(lp, logits)
    self.assertIn('bern2', dist.name)
    self.assertIsNotNone(dlpdlogits)
    self.assertGreater(
        self.evaluate(tf.reduce_sum(tf.abs(dlpdlogits))), 0)

  def testCopyUnknownRank(self):
    logits = tf1.placeholder_with_default(
        tf.random.normal([20, 3, 1, 5]), shape=None)
    dist = tfd.Bernoulli(logits=logits, name='b1')
    self.assertIn('b1', dist.name)
    dist = dist.copy(name='b2')
    self.assertIn('b2', dist.name)

  def testSliceCopyOverrideNameSliceAgainCopyOverrideLogitsSliceAgain(self):
    logits = tf.random.normal([20, 3, 2, 5])
    dist = tfd.Bernoulli(logits=logits, name='b1')
    self.assertIn('b1', dist.name)
    dist = dist[:10].copy(name='b2')
    self.assertAllEqual((10, 3, 2, 5), dist.batch_shape)
    self.assertIn('b2', dist.name)
    dist = dist.copy(name='b3')[..., 1]
    self.assertAllEqual((10, 3, 2), dist.batch_shape)
    self.assertIn('b3', dist.name)
    dist = dist.copy(logits=tf.random.normal([2]))
    self.assertAllEqual((2,), dist.batch_shape)
    self.assertIn('b3', dist.name)

  def testDocstrSliceExample(self):
    b = tfd.Bernoulli(logits=tf.zeros([3, 5, 7, 9]))  # batch shape [3, 5, 7, 9]
    self.assertAllEqual((3, 5, 7, 9), b.batch_shape)
    b2 = b[:, tf.newaxis, ..., -2:, 1::2]  # batch shape [3, 1, 5, 2, 4]
    self.assertAllEqual((3, 1, 5, 2, 4), b2.batch_shape)


@test_util.run_all_in_graph_and_eager_modes
class BernoulliFromVariableTest(test_case.TestCase):

  def testGradientLogits(self):
    x = tf.Variable([-1., 1])
    self.evaluate(x.initializer)
    d = tfd.Bernoulli(logits=x, validate_args=True)
    with tf.GradientTape() as tape:
      loss = -d.log_prob([0, 1])
    g = tape.gradient(loss, d.trainable_variables)
    self.assertLen(g, 1)
    self.assertAllNotNone(g)

  def testGradientProbs(self):
    x = tf.Variable([0.1, 0.7])
    self.evaluate(x.initializer)
    d = tfd.Bernoulli(probs=x, validate_args=True)
    with tf.GradientTape() as tape:
      loss = -d.log_prob([0, 1])
    g = tape.gradient(loss, d.trainable_variables)
    self.assertLen(g, 1)
    self.assertAllNotNone(g)

  def testAssertionsProbs(self):
    x = tf.Variable([0.1, 0.7, 0.0])
    d = tfd.Bernoulli(probs=x, validate_args=True)
    self.evaluate(x.initializer)
    self.evaluate(d.entropy())
    with tf.control_dependencies([x.assign([0.1, -0.7, 0.0])]):
      with self.assertRaisesOpError('x >= 0 did not hold'):
        self.evaluate(d.entropy())


if __name__ == '__main__':
  tf.test.main()
