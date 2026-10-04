import sys
import torch
import transformers

print("="*50)
print("Adaptive SLM Quantization - Environment test")
print("="* 50)

print("python : ",sys.version)
print("pyTorch : ",torch.__version__)
print("Transformers : ",transformers.__version__)

print("\nCUDA availability : ",torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU : ",torch.cuda.get_device_name(0))

    total_memory = torch.cuda.get_device_properties(0).total_memory
    print("Total VRAM :",round(total_memory/1024**3,2),"GB")

    print("Allocate VRAM :",round(torch.cuda.memory_allocated(0)/1024**3,2),"GB")

    print("Reserved VRAM :",round(torch.cuda.memory_reserved(0)/1024**3,2),"GB")

else:
    print("WARNING : GPU is not available")