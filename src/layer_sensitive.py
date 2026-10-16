import torch
from contextlib import contextmanager

def fake_quantize_int4(weight):
    original_shape = weight.shape

    flat =weight.float().reshape(weight.shape[0],-1)

    max_abs =flat.abs().amax(dim=1,keepdim=True)
    scale = max_abs.clamp(min=1e-8)/7.0

    quantized = torch.round(flat/scale)
    quantized =torch.clamp(quantized,-7,7)

    restored=quantized*scale

    return restored.reshape(original_shape).to(weight.dtype)

@contextmanager
def quantize_single_layer(model,layer_index):
    layer = model.model.layers[layer_index]
    originals =[]

    try:
        with torch.no_grad():
            for module in layer.modules():
                if isinstance(module,torch.nn.Linear):
                    if module.weight is None:
                        continue

                    weight =module.weight
                    originl = weight.detach().clone()
                    originals.append((weight,originl))

                    quantized = fake_quantize_int4(weight)
                    weight.copy_(quantized)

        yield model

    finally:
        with torch.no_grad():
            for weight,originl in originals:
                weight.copy_(originl)