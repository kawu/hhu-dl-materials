from typing import Tuple

import math
import torch
from torch.autograd import Function

# Tensor type, as usual
TT = torch.TensorType


################################################################
# Addition
################################################################


class Addition(Function):

    @staticmethod
    def forward(ctx, x1: TT, x2: TT) -> TT:
        return x1 + x2
        
    @staticmethod
    def backward(ctx, dzdy: TT) -> Tuple[TT, TT]:
        return dzdy, dzdy


# Make `add` an alias of the custom autograd function
add = Addition.apply

# We can check that our custom addition behaves as the one provided in PyTorch.
# First, create two one-element tensors with 1.0 and 2.0, and then perform the
# backward computation (which means that the objective is to minimize/maximize 
# their sum).
x1 = torch.tensor(1.0, requires_grad=True)
y1 = torch.tensor(2.0, requires_grad=True)
(x1 + y1).backward()

# We do the same with our custom addition function. 
x2 = torch.tensor(1.0, requires_grad=True)
y2 = torch.tensor(2.0, requires_grad=True)
add(x2, y2).backward()

assert x1.grad == x2.grad
assert y1.grad == y2.grad


# The nice part is that, since addition is element-wise, this should work also
# for complex tensors.
x1 = torch.randn(3, 3, requires_grad=True)
y1 = torch.randn(3, 3, requires_grad=True)
(x1 + y1).sum().backward()

# We use clone -> detach to get the exact copies of x1 and y1, otherwise
# not related to x1 and y1.
x2 = x1.clone().detach().requires_grad_(True)
y2 = y1.clone().detach().requires_grad_(True)
add(x2, y2).sum().backward()

# `x1.grad == x2.grad` creates a tensor of Boolean values, we use
# .all() to check that they are all True.
assert (x1.grad == x2.grad).all()
assert (y1.grad == y2.grad).all()


################################################################
# Sigmoid (logistic)
################################################################


class Sigmoid(Function):

    @staticmethod
    def forward(ctx, x: TT) -> TT:
        y = 1 / (1 + torch.exp(-x))
        ctx.save_for_backward(y)
        return y
        
    @staticmethod
    def backward(ctx, dzdy: TT) -> TT:
        y, = ctx.saved_tensors
        return dzdy * y * (1 - y)


# Alias
sigmoid = Sigmoid.apply

# Some tests to check if this works as intended
x1 = torch.randn(3, 3, requires_grad=True)
z1 = torch.sigmoid(x1).sum()
z1.backward()

x2 = x1.clone().detach().requires_grad_(True)
z2 = sigmoid(x2).sum()
z2.backward()

# Check if the results of the forward computations are equal
assert (z1 == z2).all()

# Check if sufficiently similar (clearly the backward method of the
# PyTorch sigmoid is better in terms of numerical precision).
diff = x1.grad - x2.grad
assert (-1e-5 < diff).all()
assert (diff  < 1e-5).all()


################################################################
# Sum
################################################################


class Sum(Function):

    @staticmethod
    def forward(ctx, x: TT) -> TT:
        # Save the input tensor (although its shape would be enough)
        ctx.save_for_backward(x)
        return x.sum()
        
    @staticmethod
    def backward(ctx, dzdy: TT) -> TT:
        # Restore the input tensor
        x, = ctx.saved_tensors
        # Create a tensor with the same shape as the input tensor
        # and with all values equal to dzdy.  Note how this generalizes
        # the `backward` method from the `Addition` class.
        return torch.full_like(x, dzdy)

# Alias
tsum = Sum.apply

# Checks
x1 = torch.randn(1000, 1000, requires_grad=True)
torch.sum(x1).backward()

x2 = x1.clone().detach().requires_grad_(True)
tsum(x2).backward()

assert (x1.grad - x2.grad == 0).all()


################################################################
# Dot product
#
# Represented as a coposition of two autograd functions:
# * Sum (see above)
# * Product (see below)
#
################################################################

class Product(Function):
    """Element-wise product (multiplication)"""

    @staticmethod
    def forward(ctx, x1: TT, x2: TT) -> TT:
        ctx.save_for_backward(x1, x2)
        return x1 * x2
        
    @staticmethod
    def backward(ctx, dzdy: TT) -> Tuple[TT, TT]:
        x1, x2 = ctx.saved_tensors
        # The line below implements the product rule
        # (https://en.wikipedia.org/wiki/Product_rule)
        return dzdy*x2, dzdy*x1

# Alias
prod = Product.apply

# Dot product (composition of custom autograd functions)
def dot(x: TT, y: TT) -> TT:
    return tsum(prod(x, y))

# Checks
x1 = torch.randn(10, requires_grad=True)
y1 = torch.randn(10, requires_grad=True)
z1 = torch.dot(x1, y1)
z1.backward()

x2 = x1.clone().detach().requires_grad_(True)
y2 = y1.clone().detach().requires_grad_(True)
z2 = dot(x2, y2)
z2.backward()

diff = z1 - z2
assert (-1e-5 < diff).all()
assert (diff  < 1e-5).all()

assert (x1.grad - x2.grad == 0).all()
assert (y1.grad - y2.grad == 0).all()


################################################################
# Dot product in one pass
#
# 
#
################################################################


class DotProduct(Function):

    @staticmethod
    def forward(ctx, x1: TT, x2: TT) -> TT:
        ctx.save_for_backward(x1, x2)
        return (x1 * x2).sum()
        
    @staticmethod
    def backward(ctx, dzdy: TT) -> Tuple[TT, TT]:
        # This method combines the `backward` methods from `Sum` and `Product`.
        # Note how the code is the same as in the `Product.backward`.  The
        # difference is that the `dzdy` tensor is a single-element tensor.
        assert dzdy.dim() == 0
        x1, x2 = ctx.saved_tensors
        # So when we multiply, e.g., `dzdy` by `x2`, we actually multilpy `dzdy`
        # by each element in `x2`.
        assert (dzdy * x2).shape == x2.shape
        # Return the results
        return dzdy*x2, dzdy*x1

# Alias
dot = DotProduct.apply

# Checks
x1 = torch.randn(10, requires_grad=True)
y1 = torch.randn(10, requires_grad=True)
z1 = torch.dot(x1, y1)
z1.backward()

x2 = x1.clone().detach().requires_grad_(True)
y2 = y1.clone().detach().requires_grad_(True)
z2 = dot(x2, y2)
z2.backward()

diff = z1 - z2
assert (-1e-5 < diff).all()
assert (diff  < 1e-5).all()

assert (x1.grad - x2.grad == 0).all()
assert (y1.grad - y2.grad == 0).all()


################################################################
# Matrix-vector product
################################################################


class MatrixVectorProduct(Function):

    @staticmethod
    def forward(ctx, m: TT, v: TT) -> TT:
        ctx.save_for_backward(m, v)
        return torch.mv(m, v)
        
    @staticmethod
    def backward(ctx, dzdy: TT) -> Tuple[TT, TT]:
        # Restore the inputs stored in the forward method
        m, v = ctx.saved_tensors
        # The shape of `dzdy` should be the same as the shape of the output of
        # matrix-vector product (the number of rows in `m`):
        assert dzdy.dim() == 1
        assert dzdy.shape[0] == m.shape[0]
        # Make a "column vector" from dzdy
        dzdy = dzdy.view(-1, 1)
        assert dzdy.shape == torch.Size([m.shape[0], 1])
        # The two partial derivatives below are calculated based on the idea
        # that the result of matrix-vector multiplication is a vector of dot
        # products between the individual rows in `m` and the input vector `v`.
        # Hence, the line immediately below performs a calculation equivalent
        # to the one implemented in the backward method of the DotProduct.
        # Here, however, it does it for all the rows of the input matrix `m`
        # in parallel.
        dzdm = torch.mm(dzdy, v.view(1, -1))
        # To obtain `dzdv`, multiply each row in `m` by the corresponding
        # value in `dzdy`.  Then, sum the rows of the resulting matrix.
        # It is probably best to verify this on paper.
        dzdv = (dzdy * m).sum(dim=0)
        return dzdm, dzdv

# Alias
mv = MatrixVectorProduct.apply

# Checks
m1 = torch.randn(5, 3, requires_grad=True)
v1 = torch.randn(3, requires_grad=True)
z1 = torch.mv(m1, v1)
z1.sum().backward()

m2 = m1.clone().detach().requires_grad_(True)
v2 = v1.clone().detach().requires_grad_(True)
z2 = mv(m2, v2)
z2.sum().backward()

# diff = z1 - z2
# assert (-1e-10 < diff).all()
# assert (diff  < 1e-10).all()

assert (z1 - z2 == 0).all()
assert (m1.grad - m2.grad == 0).all()
assert (v1.grad - v2.grad == 0).all()
