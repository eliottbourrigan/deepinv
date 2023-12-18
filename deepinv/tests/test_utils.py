import deepinv
import torch
import pytest





@pytest.fixture
def tensorlist():
    x = torch.ones((1, 1, 2, 2))
    y = torch.ones((1, 1, 2, 2))
    x = deepinv.utils.TensorList([x, x])
    y = deepinv.utils.TensorList([y, y])
    return x, y


def test_tensordict_sum(tensorlist):
    x, y = tensorlist
    z = torch.ones((1, 1, 2, 2)) * 2
    z1 = deepinv.utils.TensorList([z, z])
    z = x + y
    assert (z1[0] == z[0]).all() and (z1[1] == z[1]).all() 


def test_tensordict_mul(tensorlist):
    x, y = tensorlist
    z = torch.ones((1, 1, 2, 2))
    z1 = deepinv.utils.TensorList([z, z])
    z = x * y
    assert (z1[0] == z[0]).all() and (z1[1] == z[1]).all()


def test_tensordict_div(tensorlist):
    x, y = tensorlist
    z = torch.ones((1, 1, 2, 2))
    z1 = deepinv.utils.TensorList([z, z])
    z = x / y
    assert (z1[0] == z[0]).all() and (z1[1] == z[1]).all()


def test_tensordict_sub(tensorlist):
    x, y = tensorlist
    z = torch.zeros((1, 1, 2, 2))
    z1 = deepinv.utils.TensorList([z, z])
    z = x - y
    assert (z1[0] == z[0]).all() and (z1[1] == z[1]).all()


def test_tensordict_neg(tensorlist):
    x, y = tensorlist
    z = -torch.ones((1, 1, 2, 2))
    z1 = deepinv.utils.TensorList([z, z])
    z = -x
    assert (z1[0] == z[0]).all() and (z1[1] == z[1]).all()


def test_tensordict_append(tensorlist):
    x, y = tensorlist
    z = torch.ones((1, 1, 2, 2))
    z1 = deepinv.utils.TensorList([z, z, z, z])
    z = x.append(y)
    assert (z1[0] == z[0]).all() and (z1[-1] == z[-1]).all()


def test_plot():
    x = torch.ones((1, 1, 2, 2))
    imgs = [x, x]
    deepinv.utils.plot(imgs, titles=["a", "b"])
    deepinv.utils.plot(x, titles="a")
    deepinv.utils.plot(imgs)



#

import torch.nn as nn
import torch


#OPTIMIZATION

from deepinv.utils.optimization import NeuralIteration, GradientDescent, ProximalGradientDescent


class MockPhysics:
    def A_adjoint(self, x):
        return x  # Mock implementation
    
def test_neural_iteration_initialization():
    model = NeuralIteration()
    # Pass multiple identical blocks to avoid the single block issue
    backbone_blocks = [nn.Linear(10, 10), nn.Linear(10, 10)]
    model.init(backbone_blocks, step_size=0.5, iterations=2)
    assert model.iterations == 2
    assert model.step_size.size() == torch.Size([2])
    assert isinstance(model.blocks, nn.ModuleList)
    assert len(model.blocks) == 2  # Assurez-vous qu'il y a 2 blocs

def test_neural_iteration_forward():
    model = NeuralIteration()
    backbone_blocks = [nn.Linear(10, 10), nn.Linear(10, 10)]
    model.init(backbone_blocks, iterations=2)
    physics = MockPhysics()
    y = torch.randn(10, 10)
    output = model.forward(y, physics)
    assert torch.equal(output, y)  # On suppose que forward renvoie physics.A_adjoint(y)



#METRICS
    
from deepinv.utils.metric import cal_angle, cal_mse, cal_psnr, cal_psnr_complex, norm
def test_norm():
    a = torch.tensor([[[[1., 2.], [3., 4.]]]])
    expected_norm = torch.tensor([[[[5.4772]]]])
    assert torch.allclose(norm(a), expected_norm, atol=1e-4)



def test_cal_angle():
    a = torch.tensor([1., 0., 0.])
    b = torch.tensor([0., 1., 0.])
    expected_normalized_angle = 0.5  # 90 degrés normalisés (pi/2 radians / pi)
    assert cal_angle(a, b) == pytest.approx(expected_normalized_angle, rel=1e-3)


def test_cal_psnr():
    a = torch.ones((1, 1, 256, 256))
    b = torch.zeros((1, 1, 256, 256))
    max_pixel = 1.0
    expected_psnr = 20 * torch.log10(max_pixel / torch.sqrt(torch.tensor(1.0)))
    assert cal_psnr(a, b, max_pixel) == pytest.approx(expected_psnr.item(), rel=1e-3)


def test_cal_mse():
    a = torch.tensor([1., 2., 3.])
    b = torch.tensor([1., 2., 3.])
    expected_mse = 0.0
    assert cal_mse(a, b) == expected_mse


def test_cal_psnr_complex():
    a = torch.randn((1, 2, 10, 10))  # Simulated complex data
    b = torch.randn((1, 2, 10, 10))
    # Le test vérifiera si la fonction s'exécute sans erreurs
    # et retourne un résultat raisonnable, mais ne peut pas prédire la valeur exacte
    psnr_complex = cal_psnr_complex(a, b)
    assert psnr_complex > 0



#PHANTOMS
from deepinv.utils.phantoms import random_shapes, random_phantom, RandomPhantomDataset
    
def test_random_phantom_dataset_initialization():
    size = 128
    n_data = 10
    length = 100
    dataset = RandomPhantomDataset(size=size, n_data=n_data, length=length)

    assert dataset.space.shape == (size, size)
    assert dataset.n_data == n_data
    assert len(dataset) == length


def test_random_phantom_dataset_length():
    length = 100
    dataset = RandomPhantomDataset(length=length)
    assert len(dataset) == length



def test_random_phantom_dataset_getitem():
    dataset = RandomPhantomDataset()
    phantom, _ = dataset[0]

    assert isinstance(phantom, torch.Tensor)
    # Vérifiez d'autres propriétés, comme les dimensions, si nécessaire


#PARAMETERS
    
import numpy as np
import pytest
from deepinv.utils.parameters import get_DPIR_params, get_GSPnP_params

def test_get_DPIR_params():
    noise_level_img = 0.05
    lamb, sigma_denoiser, stepsize, max_iter = get_DPIR_params(noise_level_img)

    assert lamb == pytest.approx(1 / 0.23)
    assert len(sigma_denoiser) == 8
    assert len(stepsize) == 8
    assert max_iter == 8
    assert all(s >= 0 for s in sigma_denoiser)
    assert all(s >= 0 for s in stepsize)




def test_get_GSPnP_params_deblur():
    problem = "deblur"
    noise_level_img = 0.05
    lamb, sigma_denoiser, stepsize, max_iter = get_GSPnP_params(problem, noise_level_img)

    assert max_iter == 500
    assert sigma_denoiser == pytest.approx(1.8 * noise_level_img)
    assert lamb == pytest.approx(1 / 0.1)
    assert stepsize == 1.0

def test_get_GSPnP_params_super_resolution():
    problem = "super-resolution"
    noise_level_img = 0.05
    lamb, sigma_denoiser, stepsize, max_iter = get_GSPnP_params(problem, noise_level_img)

    assert max_iter == 500
    assert sigma_denoiser == pytest.approx(2.0 * noise_level_img)
    assert lamb == pytest.approx(1 / 0.065)
    assert stepsize == 1.0

def test_get_GSPnP_params_inpaint():
    problem = "inpaint"
    noise_level_img = 0.05
    lamb, sigma_denoiser, stepsize, max_iter = get_GSPnP_params(problem, noise_level_img)

    assert max_iter == 100
    assert sigma_denoiser == pytest.approx(10.0 / 255)
    assert lamb == pytest.approx(1 / 0.1)
    assert stepsize == 1.0


def test_get_GSPnP_params_invalid():
    with pytest.raises(ValueError):
        get_GSPnP_params("invalid_problem", 0.05)
