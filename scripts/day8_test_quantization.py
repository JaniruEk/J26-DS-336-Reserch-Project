import torch
import torch.nn as nn
import bitsandbytes as bnb

assert  torch.cuda.is_available()

device = "cuda"

print("GPU : ",torch.cuda.get_device_name(0))

# Create an example linear layer
original = nn.Linear(128,128,bias=False).half()


# Create a real INT4 module
int4_layer = bnb.nn.Linear4bit(
    128,
    128,
    bias=False,
    compute_dtype=torch.float16,
    quant_type="nf4"
)

int4_layer.load_state_dict(original.state_dict())
int4_layer = int4_layer.to(device)


int8_layer = bnb.nn.Linear8bitLt(
    128,
    128,
    bias=False,
    has_fp16_weights=False,
    threshold=6.0
)

int8_layer.load_state_dict(original.state_dict())
int8_layer = int8_layer.to(device)      

# STEP 5 - Verify actual weight formats
print("\nINT4 module:", type(int4_layer).__name__)
print("INT4 weight dtype:", int4_layer.weight.dtype)
print("INT4 quantization state:",
      int4_layer.weight.quant_state is not None)

print("\nINT8 module:", type(int8_layer).__name__)
print("INT8 weight dtype:", int8_layer.weight.dtype)

# STEP 6 - Test inference
x = torch.randn(1, 128, device=device, dtype=torch.float16)

with torch.inference_mode():
    output4 = int4_layer(x)
    output8 = int8_layer(x)

print("\nINT4 output shape:", output4.shape)
print("INT8 output shape:", output8.shape)

print("\nDay 8 quantization test completed!")
