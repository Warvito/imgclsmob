"""Fully Convolutional Network with Stride of 8"""
from __future__ import division
from mxnet.gluon import nn
from mxnet.context import cpu
from mxnet.gluon.nn import HybridBlock
from .oth_segbase import SegBaseModel

__all__ = ['FCN', 'get_fcn', 'oth_fcn_resnet50_voc', 'oth_fcn_resnet101_voc',
           'oth_fcn_resnet101_coco', 'oth_fcn_resnet50_ade', 'oth_fcn_resnet101_ade']


class FCN(SegBaseModel):
    r"""Fully Convolutional Networks for Semantic Segmentation

    Parameters
    ----------
    nclass : int
        Number of categories for the training dataset.
    backbone : string
        Pre-trained dilated backbone network type (default:'resnet50'; 'resnet50',
        'resnet101' or 'resnet152').
    norm_layer : object
        Normalization layer used in backbone network (default: :class:`mxnet.gluon.nn.BatchNorm`;
    norm_kwargs : dict
        Additional `norm_layer` arguments, for example `num_devices=4`
        for :class:`mxnet.gluon.contrib.nn.SyncBatchNorm`.
    pretrained_base : bool or str
        Refers to if the FCN backbone or the encoder is pretrained or not. If `True`,
        model weights of a model that was trained on ImageNet is loaded.


    Reference:

        Long, Jonathan, Evan Shelhamer, and Trevor Darrell. "Fully convolutional networks
        for semantic segmentation." *CVPR*, 2015
    """
    # pylint: disable=arguments-differ
    def __init__(self, nclass, backbone='resnet50', aux=True, ctx=cpu(), pretrained_base=True,
                 base_size=520, crop_size=480, **kwargs):
        super(FCN, self).__init__(nclass, aux, backbone, ctx=ctx, base_size=base_size,
                                  crop_size=crop_size, pretrained_base=pretrained_base, **kwargs)
        if "fixed_size" in kwargs:
            del kwargs["fixed_size"]
        if "classes" in kwargs:
            del kwargs["classes"]
        if "in_channels" in kwargs:
            del kwargs["in_channels"]
        with self.name_scope():
            self.head = _FCNHead(2048, nclass, **kwargs)
            self.head.initialize(ctx=ctx)
            self.head.collect_params().setattr('lr_mult', 10)
            if self.aux:
                self.auxlayer = _FCNHead(1024, nclass, **kwargs)
                self.auxlayer.initialize(ctx=ctx)
                self.auxlayer.collect_params().setattr('lr_mult', 10)

    def hybrid_forward(self, F, x):
        self._up_kwargs['height'] = x.shape[2]
        self._up_kwargs['width'] = x.shape[3]

        c3, c4 = self.base_forward(x)

        outputs = []
        x = self.head(c4)
        x = F.contrib.BilinearResize2D(x, **self._up_kwargs)
        outputs.append(x)

        if self.aux:
            auxout = self.auxlayer(c3)
            auxout = F.contrib.BilinearResize2D(auxout, **self._up_kwargs)
            outputs.append(auxout)
        else:
            return outputs[0]
        return tuple(outputs)


class _FCNHead(HybridBlock):
    # pylint: disable=redefined-outer-name
    def __init__(self, in_channels, channels, norm_layer=nn.BatchNorm, norm_kwargs=None, **kwargs):
        super(_FCNHead, self).__init__()
        with self.name_scope():
            self.block = nn.HybridSequential()
            inter_channels = in_channels // 4
            with self.block.name_scope():
                self.block.add(nn.Conv2D(in_channels=in_channels, channels=inter_channels,
                                         kernel_size=3, padding=1, use_bias=False))
                self.block.add(norm_layer(in_channels=inter_channels,
                                          **({} if norm_kwargs is None else norm_kwargs)))
                self.block.add(nn.Activation('relu'))
                self.block.add(nn.Dropout(0.1))
                self.block.add(nn.Conv2D(in_channels=inter_channels, channels=channels,
                                         kernel_size=1))

    # pylint: disable=arguments-differ
    def hybrid_forward(self, F, x):
        return self.block(x)


def get_fcn(dataset='pascal_voc', backbone='resnet50', pretrained=False,
            root='~/.mxnet/models', ctx=cpu(0), pretrained_base=True, num_class=150, **kwargs):
    r"""FCN model from the paper `"Fully Convolutional Network for semantic segmentation"
    <https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf>`_

    Parameters
    ----------
    dataset : str, default pascal_voc
        The dataset that model pretrained on. (pascal_voc, ade20k)
    pretrained : bool or str
        Boolean value controls whether to load the default pretrained weights for model.
        String value represents the hashtag for a certain version of pretrained weights.
    ctx : Context, default CPU
        The context in which to load the pretrained weights.
    root : str, default '~/.mxnet/models'
        Location for keeping the model parameters.
    pretrained_base : bool or str, default True
        This will load pretrained backbone network, that was trained on ImageNet.
    """
    acronyms = {
        'pascal_voc': 'voc',
        'pascal_aug': 'voc',
        'ade20k': 'ade',
        'coco': 'coco',
    }
    # from ..data import datasets
    # infer number of classes
    model = FCN(num_class, backbone=backbone, pretrained_base=pretrained_base,
                ctx=ctx, **kwargs)
    # if pretrained:
    #     from .model_store import get_model_file
    #     model.load_parameters(get_model_file(
    #         'fcn_%s_%s'%(backbone, acronyms[dataset]), tag=pretrained, root=root), ctx=ctx)
    return model

def oth_fcn_resnet50_voc(**kwargs):
    r"""FCN model with base network ResNet-50 pre-trained on Pascal VOC dataset
    from the paper `"Fully Convolutional Network for semantic segmentation"
    <https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf>`_

    Parameters
    ----------
    pretrained : bool or str
        Boolean value controls whether to load the default pretrained weights for model.
        String value represents the hashtag for a certain version of pretrained weights.
    ctx : Context, default CPU
        The context in which to load the pretrained weights.
    root : str, default '~/.mxnet/models'
        Location for keeping the model parameters.
    """
    return get_fcn('pascal_voc', 'resnet50', num_class=21, **kwargs)

def oth_fcn_resnet101_coco(**kwargs):
    r"""FCN model with base network ResNet-101 pre-trained on Pascal VOC dataset
    from the paper `"Fully Convolutional Network for semantic segmentation"
    <https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf>`_

    Parameters
    ----------
    pretrained : bool or str
        Boolean value controls whether to load the default pretrained weights for model.
        String value represents the hashtag for a certain version of pretrained weights.
    ctx : Context, default CPU
        The context in which to load the pretrained weights.
    root : str, default '~/.mxnet/models'
        Location for keeping the model parameters.
    """
    return get_fcn('coco', 'resnet101', num_class=21, **kwargs)


def oth_fcn_resnet101_voc(**kwargs):
    r"""FCN model with base network ResNet-101 pre-trained on Pascal VOC dataset
    from the paper `"Fully Convolutional Network for semantic segmentation"
    <https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf>`_

    Parameters
    ----------
    pretrained : bool or str
        Boolean value controls whether to load the default pretrained weights for model.
        String value represents the hashtag for a certain version of pretrained weights.
    ctx : Context, default CPU
        The context in which to load the pretrained weights.
    root : str, default '~/.mxnet/models'
        Location for keeping the model parameters.
    """
    return get_fcn('pascal_voc', 'resnet101', num_class=21, **kwargs)

def oth_fcn_resnet50_ade(**kwargs):
    r"""FCN model with base network ResNet-50 pre-trained on ADE20K dataset
    from the paper `"Fully Convolutional Network for semantic segmentation"
    <https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf>`_

    Parameters
    ----------
    pretrained : bool or str
        Boolean value controls whether to load the default pretrained weights for model.
        String value represents the hashtag for a certain version of pretrained weights.
    ctx : Context, default CPU
        The context in which to load the pretrained weights.
    root : str, default '~/.mxnet/models'
        Location for keeping the model parameters.
    """
    return get_fcn('ade20k', 'resnet50', num_class=150, **kwargs)

def oth_fcn_resnet101_ade(**kwargs):
    r"""FCN model with base network ResNet-50 pre-trained on ADE20K dataset
    from the paper `"Fully Convolutional Network for semantic segmentation"
    <https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf>`_

    Parameters
    ----------
    pretrained : bool or str
        Boolean value controls whether to load the default pretrained weights for model.
        String value represents the hashtag for a certain version of pretrained weights.
    ctx : Context, default CPU
        The context in which to load the pretrained weights.
    root : str, default '~/.mxnet/models'
        Location for keeping the model parameters.
    """
    return get_fcn('ade20k', 'resnet101', num_class=150, **kwargs)
