import torch
import torch.nn as nn

import quant_cuda
import os
os.environ['CUDA_LAUNCH_BLOCKING'] = "1"

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

print('Benchmarking LLaMa-7B FC2 matvec ...')

DEV = torch.device('cuda:0')

B = 4
L = 512
M = 4096
N = 11008

DTYPE = torch.half
mat = torch.randn((M, N), device=DEV, dtype=DTYPE)
vec = torch.randn((B, M), device=DEV, dtype=DTYPE)
mul = torch.zeros((B, N), device=DEV, dtype=DTYPE)

COUNT = 1000
import time
tick = time.time()
for _ in range(COUNT):
    torch.matmul(vec, mat, out=mul) 
    torch.cuda.synchronize()
print('FP16:', (time.time() - tick) / COUNT)

DTYPE = torch.float
mat = mat.to(DTYPE)
vec = vec.to(DTYPE)
mul = mul.to(DTYPE)

mat = torch.randint(-1000000000, 1000000000, (M // 32 * 2, N), device=DEV, dtype=torch.int)
scales = torch.randn(N, device=DEV, dtype=DTYPE)
zeros = torch.randint(-1000000000, 1000000000,(1,N // 32 * 2), device=DEV,dtype=torch.int32)
g_idx = torch.zeros(M, device=DEV, dtype=torch.int32)
COUNT = 1000
import time
vec = vec.float()
tick = time.time()
for _ in range(COUNT):
    quant_cuda.vecquant2matmul(vec, mat, mul, scales, zeros, g_idx)
    torch.cuda.synchronize()
print('2bit:', (time.time() - tick) / COUNT)

mat = torch.randint(-1000000000, 1000000000, (M // 32 * 3, N), device=DEV, dtype=torch.int)
scales = torch.randn(N, device=DEV, dtype=DTYPE)
zeros = torch.randint(-1000000000, 1000000000,(1,N // 32 * 3), device=DEV,dtype=torch.int32)

vec = vec.float()
tick = time.time()
for _ in range(COUNT):
    quant_cuda.vecquant3matmul(vec, mat, mul, scales, zeros, g_idx)
    torch.cuda.synchronize()
print('3bit:', (time.time() - tick) / COUNT)

mat = torch.randint(-1000000000, 1000000000, (M // 32 * 4, N), device=DEV, dtype=torch.int)
scales = torch.randn(N, device=DEV, dtype=DTYPE)
zeros = torch.randint(-1000000000, 1000000000,(1,N // 32 * 4), device=DEV,dtype=torch.int32)

vec = vec.float()
tick = time.time()
for _ in range(COUNT):
    quant_cuda.vecquant4matmul(vec, mat, mul, scales, zeros, g_idx)
    torch.cuda.synchronize()
print('4bit:', (time.time() - tick) / COUNT)

mat = torch.randint(-1000000000, 1000000000, (M // 32 * 8, N), device=DEV, dtype=torch.int)
scales = torch.randn(N, device=DEV, dtype=DTYPE)
zeros = torch.randint(-1000000000, 1000000000,(1,N // 32 * 8), device=DEV,dtype=torch.int32)

vec = vec.float()
tick = time.time()
for _ in range(COUNT):
    quant_cuda.vecquant8matmul(vec, mat, mul, scales, zeros, g_idx)
    torch.cuda.synchronize()
print('8bit:', (time.time() - tick) / COUNT)
print('Verifiying kernel correctness ...')

M = 4096
N = 11008

from quant import *

layer = nn.Linear(M, N)
vec = torch.randn(B,L,M).to(DEV).half()

quantizer = Quantizer()
quantizer.configure(2, perchannel=True, sym=False, mse=False)
quantizer.find_params(layer.weight.data, weight=True)
layer.weight.data = quantize(layer.weight.data, quantizer.scale, quantizer.zero, quantizer.maxq)

qlayer = QuantLinear(2, -1, layer.in_features, layer.out_features, layer.bias is not None,kernel_switch_threshold = False, is_trioton = False, is_cuda = True)
qlayer.pack(layer, quantizer.scale, quantizer.zero)

qlayer = qlayer.to(DEV)
layer = layer.to(DEV).half()

with torch.no_grad():
    print('2bit Simu:', layer(vec))
    print('2bit Kern:', qlayer(vec))

layer = nn.Linear(M, N)
vec = torch.randn(B,L,M).to(DEV).half()

quantizer = Quantizer()
quantizer.configure(3, perchannel=True, sym=False, mse=False)
quantizer.find_params(layer.weight.data, weight=True)
layer.weight.data = quantize(layer.weight.data, quantizer.scale, quantizer.zero, quantizer.maxq)

qlayer = QuantLinear(3, -1, layer.in_features, layer.out_features, layer.bias is not None,kernel_switch_threshold = False, is_trioton = False, is_cuda = True)
qlayer.pack(layer, quantizer.scale, quantizer.zero)

qlayer = qlayer.to(DEV)
layer = layer.to(DEV).half()

with torch.no_grad():
    print('3bit Simu:', layer(vec))
    print('3bit Kern:', qlayer(vec))
    
layer = nn.Linear(M, N)
vec = torch.randn(B,L,M).to(DEV).half()

quantizer = Quantizer()
quantizer.configure(4, perchannel=True, sym=False, mse=False)
quantizer.find_params(layer.weight.data, weight=True)
layer.weight.data = quantize(layer.weight.data, quantizer.scale, quantizer.zero, quantizer.maxq)

qlayer = QuantLinear(4, -1, layer.in_features, layer.out_features, layer.bias is not None,kernel_switch_threshold = False, is_trioton = False, is_cuda = True)
qlayer.pack(layer, quantizer.scale, quantizer.zero)

qlayer = qlayer.to(DEV)
layer = layer.to(DEV).half()

with torch.no_grad():
    print('4bit Simu:', layer(vec))
    print('4bit Kern:', qlayer(vec))
    
layer = nn.Linear(M, N)
vec = torch.randn(B,L,M).to(DEV).half()

quantizer = Quantizer()
quantizer.configure(8, perchannel=True, sym=False, mse=False)
quantizer.find_params(layer.weight.data, weight=True)
layer.weight.data = quantize(layer.weight.data, quantizer.scale, quantizer.zero, quantizer.maxq)

qlayer = QuantLinear(8, -1, layer.in_features, layer.out_features, layer.bias is not None,kernel_switch_threshold = False, is_trioton = False, is_cuda = True)
qlayer.pack(layer, quantizer.scale, quantizer.zero)

qlayer = qlayer.to(DEV)
layer = layer.to(DEV).half()

with torch.no_grad():
    print('8bit Simu:', layer(vec))
    print('8bit Kern:', qlayer(vec))
