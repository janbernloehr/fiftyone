"""
Data utilities.

| Copyright 2017-2020, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *

# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import logging
import os

import eta.core.datasets as etads
import eta.core.image as etai
import eta.core.serial as etas
import eta.core.utils as etau

import fiftyone as fo
import fiftyone.core.utils as fou
import fiftyone.types as fot

from .parsers import (
    UnlabeledImageSampleParser,
    LabeledImageSampleParser,
    ImageClassificationSampleParser,
    ImageDetectionSampleParser,
    ImageLabelsSampleParser,
)


logger = logging.getLogger(__name__)


def parse_labeled_images(
    samples,
    dataset_dir,
    sample_parser=None,
    num_samples=None,
    image_format=None,
):
    """Parses the given labeled image samples, writing the images to disk in
    the specified directory and returning their paths and associated
    :class:`fiftyone.core.labels.Label` instances in-memory.

    Args:
        samples: an iterable of samples
        dataset_dir: the directory to which to write the images
        sample_parser (None): a :class:`LabeledImageSampleParser`
            instance whose :func:`LabeledImageSampleParser.parse` method
            will be used to parse the samples. If not provided, the default
            :class:`LabeledImageSampleParser` instance is used
        num_samples (None): the number of samples in ``samples``. If omitted,
            this is computed (if possible) via ``len(samples)``
        image_format (``fiftyone.config.default_image_ext``): the image format
            to use to write the images to disk

    Returns:
        the list of ``(image_path, label)`` tuples that were parsed
    """
    if sample_parser is None:
        sample_parser = LabeledImageSampleParser()

    num_samples, image_format, uuid_patt = _parse_args(
        samples, num_samples, image_format
    )

    images_patt = os.path.join(dataset_dir, uuid_patt + image_format)

    logger.info(
        "Parsing labeled image samples and writing images to '%s'...",
        dataset_dir,
    )

    _samples = []
    with fou.ProgressBar(total=num_samples) as pb:
        for idx, sample in enumerate(pb(samples), 1):
            img, label = sample_parser.parse(sample)
            image_path = images_patt % idx
            etai.write(img, image_path)
            _samples.append((image_path, label))

    logger.info("Parsing complete")

    return _samples


def to_images_dir(
    samples,
    dataset_dir,
    sample_parser=None,
    num_samples=None,
    image_format=None,
):
    """Writes the given images to disk in the given directory.

    Args:
        samples: an iterable of samples
        dataset_dir: the directory to which to write the images
        sample_parser (None): a :class:`UnlabeledImageSampleParser`
            instance whose :func:`UnlabeledImageSampleParser.parse` method
            will be used to parse the samples. If not provided, the default
            :class:`UnlabeledImageSampleParser` instance is used
        num_samples (None): the number of samples in ``samples``. If omitted,
            this is computed (if possible) via ``len(samples)``
        image_format (``fiftyone.config.default_image_ext``): the image format
            to use to write the images to disk

    Returns:
        the list of image paths that were written
    """
    if sample_parser is None:
        sample_parser = UnlabeledImageSampleParser()

    num_samples, image_format, uuid_patt = _parse_args(
        samples, num_samples, image_format
    )

    images_patt = os.path.join(dataset_dir, uuid_patt + image_format)

    logger.info("Writing images to '%s'...", dataset_dir)

    image_paths = []
    with fou.ProgressBar(total=num_samples) as pb:
        for idx, sample in enumerate(pb(samples), 1):
            img = sample_parser.parse(sample)
            image_path = images_patt % idx
            etai.write(img, image_path)
            image_paths.append(image_path)

    logger.info("Images written")

    return image_paths


def to_image_classification_dataset(
    samples,
    dataset_dir,
    sample_parser=None,
    num_samples=None,
    image_format=None,
):
    """Writes the given samples to disk as an image classification dataset.

    See :class:`fiftyone.types.ImageClassificationDataset` for format details.

    Args:
        samples: an iterable of samples
        dataset_dir: the directory to which to write the dataset
        sample_parser (None): a :class:`ImageClassificationSampleParser`
            instance whose :func:`ImageClassificationSampleParser.parse` method
            will be used to parse the samples. If not provided, the default
            :class:`ImageClassificationSampleParser` instance is used
        num_samples (None): the number of samples in ``samples``. If omitted,
            this is computed (if possible) via ``len(samples)``
        image_format (``fiftyone.config.default_image_ext``): the image format
            to use to write the images to disk
    """
    if sample_parser is None:
        sample_parser = ImageClassificationSampleParser()

    num_samples, image_format, uuid_patt = _parse_args(
        samples, num_samples, image_format
    )
    classes, labels_map_rev = _parse_classes(sample_parser)

    data_dir = os.path.join(dataset_dir, "data")
    images_patt = os.path.join(data_dir, uuid_patt + image_format)
    labels_path = os.path.join(dataset_dir, "labels.json")

    logger.info(
        "Writing samples to '%s' in '%s' format...",
        dataset_dir,
        etau.get_class_name(fot.ImageClassificationDataset),
    )

    etau.ensure_dir(data_dir)
    labels_dict = {}
    with fou.ProgressBar(total=num_samples) as pb:
        for idx, sample in enumerate(pb(samples), 1):
            img, label = sample_parser.parse(sample)
            etai.write(img, images_patt % idx)
            labels_dict[uuid_patt % idx] = _parse_classification(
                label, labels_map_rev=labels_map_rev
            )

    logger.info("Writing labels to '%s'", labels_path)
    labels = {
        "classes": classes,
        "labels": labels_dict,
    }
    etas.write_json(labels, labels_path)

    logger.info("Dataset created")


def to_image_detection_dataset(
    samples,
    dataset_dir,
    sample_parser=None,
    num_samples=None,
    image_format=None,
):
    """Writes the given samples to disk as an image detection dataset.

    See :class:`fiftyone.types.ImageDetectionDataset` for format details.

    Args:
        samples: an iterable of samples
        dataset_dir: the directory to which to write the dataset
        sample_parser (None): a :class:`ImageDetectionSampleParser` instance
            whose :func:`ImageDetectionSampleParser.parse` method will be
            used to parse the samples. If not provided, the default
            :class:`ImageDetectionSampleParser` instance is used
        num_samples (None): the number of samples in ``samples``. If omitted,
            this is computed (if possible) via ``len(samples)``
        image_format (``fiftyone.config.default_image_ext``): the image format
            to use to write the images to disk
    """
    if sample_parser is None:
        sample_parser = ImageDetectionSampleParser()

    num_samples, image_format, uuid_patt = _parse_args(
        samples, num_samples, image_format
    )
    classes, labels_map_rev = _parse_classes(sample_parser)

    data_dir = os.path.join(dataset_dir, "data")
    images_patt = os.path.join(data_dir, uuid_patt + image_format)
    labels_path = os.path.join(dataset_dir, "labels.json")

    logger.info(
        "Writing samples to '%s' in '%s' format...",
        dataset_dir,
        etau.get_class_name(fot.ImageDetectionDataset),
    )

    etau.ensure_dir(data_dir)
    labels_dict = {}
    with fou.ProgressBar(total=num_samples) as pb:
        for idx, sample in enumerate(pb(samples), 1):
            img, label = sample_parser.parse(sample)
            etai.write(img, images_patt % idx)
            labels_dict[uuid_patt % idx] = _parse_detections(
                label, labels_map_rev=labels_map_rev
            )

    logger.info("Writing labels to '%s'", labels_path)
    labels = {
        "classes": classes,
        "labels": labels_dict,
    }
    etas.write_json(labels, labels_path)

    logger.info("Dataset created")


def to_image_labels_dataset(
    samples,
    dataset_dir,
    sample_parser=None,
    num_samples=None,
    image_format=None,
):
    """Writes the given samples to disk as a multitask image labels dataset.

    See :class:`fiftyone.types.ImageLabelsDataset` for format details.

    Args:
        samples: an iterable of samples
        dataset_dir: the directory to which to write the
            ``eta.core.datasets.LabeledImageDataset``
        sample_parser (None): a :class:`ImageLabelsSampleParser` instance whose
            :func:`ImageLabelsSampleParser.parse` method will be used to parse
            the samples. If not provided, the default
            :class:`ImageLabelsSampleParser` instance is used
        num_samples (None): the number of samples in ``samples``. If omitted,
            this is computed (if possible) via ``len(samples)``
        image_format (``fiftyone.config.default_image_ext``): the image format
            to use to write the images to disk
    """
    if sample_parser is None:
        sample_parser = ImageLabelsSampleParser()

    num_samples, image_format, uuid_patt = _parse_args(
        samples, num_samples, image_format
    )

    images_patt = uuid_patt + image_format
    labels_patt = uuid_patt + ".json"

    logger.info(
        "Writing samples to '%s' in '%s' format...",
        dataset_dir,
        etau.get_class_name(fot.ImageLabelsDataset),
    )

    lid = etads.LabeledImageDataset.create_empty_dataset(dataset_dir)
    with fou.ProgressBar(total=num_samples) as pb:
        for idx, sample in enumerate(pb(samples), 1):
            img, label = sample_parser.parse(sample)
            image_labels = _parse_image_labels(label)
            lid.add_data(
                img, image_labels, images_patt % idx, labels_patt % idx
            )

    logger.info("Writing manifest to '%s'", lid.manifest_path)
    lid.write_manifest()

    logger.info("Dataset created")


def _parse_args(samples, num_samples, image_format):
    if num_samples is None:
        try:
            num_samples = len(samples)
        except:
            pass

    if image_format is None:
        image_format = fo.config.default_image_ext

    if num_samples:
        uuid_patt = etau.get_int_pattern_with_capacity(num_samples)
    else:
        uuid_patt = fo.config.default_sequence_idx

    return num_samples, image_format, uuid_patt


def _parse_classes(sample_parser):
    classes = sample_parser.classes
    if classes is not None:
        labels_map_rev = {c: i for i, c in enumerate(classes)}
    else:
        labels_map_rev = None

    return classes, labels_map_rev


def _parse_classification(classification, labels_map_rev=None):
    label = classification.label
    if labels_map_rev is not None:
        label = labels_map_rev[label]

    return label


def _parse_detections(detections, labels_map_rev=None):
    _detections = []
    for detection in detections.detections:
        label = detection.label
        if labels_map_rev is not None:
            label = labels_map_rev[label]

        _detection = {
            "label": label,
            "bounding_box": detection.bounding_box,
        }
        if detection.confidence is not None:
            _detection["confidence"] = detection.confidence

        _detections.append(_detection)

    return _detections


def _parse_image_labels(label):
    return label.labels
