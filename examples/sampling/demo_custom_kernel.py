r"""
Building your custom sampling algorithm.
====================================================================================================

This code shows you how to build your custom sampling kernel.

"""

import deepinv as dinv
from deepinv.utils.plotting import plot
import torch
import torchvision
import requests
from imageio.v2 import imread
from io import BytesIO
import numpy as np

# %%
# Load image from the internet
# --------------------------------------------
#
# This example uses an image of Lionel Messi from Wikipedia.

device = dinv.utils.get_freer_gpu() if torch.cuda.is_available() else "cpu"

url = (
    "https://upload.wikimedia.org/wikipedia/commons/b/b4/"
    "Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg"
)
res = requests.get(url)
x = imread(BytesIO(res.content)) / 255.0

x = torch.tensor(x, device=device, dtype=torch.float).permute(2, 0, 1).unsqueeze(0)
x = torch.nn.functional.interpolate(
    x, scale_factor=0.5
)  # reduce the image size for faster eval
x = torchvision.transforms.functional.center_crop(x, 32)

# %%
# Define forward operator and noise model
# --------------------------------------------------------------
#
# This example uses inpainting as the forward operator and Gaussian noise as the noise model.

sigma = 0.1  # noise level
physics = dinv.physics.Inpainting(mask=0.5, tensor_size=x.shape[1:], device=device)
physics.noise_model = dinv.physics.GaussianNoise(sigma=sigma)


# %%
# Define the likelihood
# --------------------------------------------------------------
#
# Since the noise model is Gaussian, the negative log-likelihood is the L2 loss.
#
# .. math::
#   -\log p(y|x) \propto \frac{1}{2\sigma^2} \|y-Ax\|^2

# load Gaussian Likelihood
likelihood = dinv.optim.L2(sigma=sigma)

# %%
# Define the prior
# -------------------------------------------
#
# The score a distribution can be approximated using Tweedie's formula via the
# :class:`deepinv.models.ScoreDenoiser` class.
#
# .. math::
#
#           - \nabla \log p_{\sigma}(x) \approx \frac{1}{\sigma^2} \left(x - D(x)\right)
#
# This example uses a pretrained DnCNN model.
# From a Bayesian point of view, the score plays the role of the gradient of the
# negative log prior
# The hyperparameter ``sigma_denoiser`` controls the strength of the prior.

model_spec = {
    "name": "dncnn",
    "args": {
        "device": device,
        "in_channels": 3,
        "out_channels": 3,
        "pretrained": "download_lipschitz",
    },
}

sigma_denoiser = 2 / 255
prior = dinv.models.ScoreDenoiser(model_spec=model_spec)

# %%
# Define the sampling iteration
# --------------------------------------------------------------
#
# Define custom sampling kernel (possibly a Markov kernel which depends on the previous sample).


class AdjustedULAIterator(torch.nn.Module):
    def __init__(self, step_size, alpha, sigma):
        super().__init__()
        self.step_size = step_size
        self.alpha = alpha
        self.noise_std = np.sqrt(2 * step_size)
        self.sigma = sigma

    def forward(self, x, y, physics, likelihood, prior):
        noise = torch.randn_like(x) * self.noise_std
        lhood = -likelihood.grad(x, y, physics)
        lprior = -prior(x, self.sigma) * self.alpha
        proposal = x + self.step_size * (lhood + lprior) + noise
        return x if torch.rand(1) < torch.exp(-self.alpha * (lprior + lhood)) else proposal


class MySampler(dinv.sampling.MonteCarlo):
    def __init__(self, prior, data_fidelity, alpha, sigma,
                 max_iter=1e3, burnin_ratio=.1, clip=(-1, 2), verbose=True):
        # generate an iterator
        iterator = MALAIterator(step_size=step_size, alpha=alpha, sigma=sigma)
        # set the params of the base class
        super().__init__(iterator, prior, data_fidelity, max_iter=max_iter,
                         burnin_ratio=burnin_ratio, clip=clip, verbose=verbose)


regularization = 0.9
step_size = 0.01 * (sigma**2)
iterations = int(5e3) if torch.cuda.is_available() else 10
f = dinv.sampling.ULA(
    prior=prior,
    data_fidelity=likelihood,
    max_iter=iterations,
    alpha=regularization,
    step_size=step_size,
    verbose=True,
    sigma=sigma_denoiser,
)

# %%
# Generate the measurement
# --------------------------------------------------------------
# We apply the forward model to generate the noisy measurement.

y = physics(x)


# %%
# Run sampling algorithm and plot results
# --------------------------------------------------------------
# The sampling algorithm returns the posterior mean and variance.
# We compare the posterior mean with a simple linear reconstruction.

mean, var = f(y, physics)

# compute linear inverse
x_lin = physics.A_adjoint(y)

# compute PSNR
print(f"Linear reconstruction PSNR: {dinv.utils.metric.cal_psnr(x, x_lin):.2f} dB")
print(f"Posterior mean PSNR: {dinv.utils.metric.cal_psnr(x, mean):.2f} dB")

# plot results
error = (mean - x).abs().sum(dim=1).unsqueeze(1)  # per pixel average abs. error
std = var.sum(dim=1).unsqueeze(1).sqrt()  # per pixel average standard dev.
imgs = [x_lin, x, mean, std / std.flatten().max(), error / error.flatten().max()]
plot(
    imgs,
    titles=["measurement", "ground truth", "post. mean", "post. std", "abs. error"],
)
