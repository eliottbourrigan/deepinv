from deepinv.physics.forward import DecomposablePhysics
import torch


class Inpainting(DecomposablePhysics):
    r"""

    Inpainting forward operator, keeps a subset of entries.

    The operator is described by the diagonal matrix

    .. math::

        A = \text{diag}(m) \in \mathbb{R}^{n\times n}

    where :math:`m` is a binary mask with n entries.

    This operator is linear and has a trivial SVD decomposition, which allows for fast computation
    of the pseudo-inverse and proximal operator.

    An existing operator can be loaded from a saved ``.pth`` file via ``self.load_state_dict(save_path)``,
    in a similar fashion to ``torch.nn.Module``.

    :param tuple tensor_size: size of the input images, e.g., (C, H, W).
    :param torch.tensor, float mask: If the input is a float, the entries of the mask will be sampled from a bernoulli
        distribution with probability equal to ``mask``. If the input is a ``torch.tensor`` matching tensor_size,
        the mask will be set to this tensor.
    :param torch.device device: gpu or cpu
    :param bool pixelwise: Apply the mask in a pixelwise fashion, i.e., zero all channels in a given pixel simultaneously.

    :Examples:
    >>> x = torch.rand((1, 3, 5, 5))
    >>> # Inpainting Operator with defined mask
    >>> inpainting_defined_mask = Inpainting((3, 5, 5), mask=torch.Tensor([1, 0, 1, 0, 1]))
    >>> inpainting_defined_mask(x)[0,0,0,1].item() == 0.0
    True
    >>> # Inpainting Operator with mask rate 1.0
    >>> inpainting_1_mask_rate = Inpainting((3, 5, 5), mask=1.0)
    >>> torch.sum(inpainting_1_mask_rate(x)).item() == torch.sum(x).item()
    True
    >>> # Inpainting Operator with mask rate 0.0
    >>> inpainting_0_mask_rate = Inpainting((3, 5, 5), mask=0.0)
    >>> torch.sum(inpainting_0_mask_rate(x)).item() == 0.0
    True
    """

    def __init__(self, tensor_size, mask=0.3, pixelwise=True, device="cpu", **kwargs):
        super().__init__(**kwargs)
        self.tensor_size = tensor_size

        if isinstance(mask, torch.Tensor):  # check if the user created mask
            self.mask = mask
        else:  # otherwise create new random mask
            mask_rate = mask
            self.mask = torch.ones(tensor_size, device=device)
            aux = torch.rand_like(self.mask)
            if not pixelwise:
                self.mask[aux > mask_rate] = 0
            else:
                self.mask[:, aux[0, :, :] > mask_rate] = 0

        self.mask = torch.nn.Parameter(
            self.mask.unsqueeze(0), requires_grad=False)


if __name__ == '__main__':
    import doctest
    import collections
    collections.Callable = collections.abc.Callable
    doctest.testmod(verbose=True)
