def fnv(data: bytes, hval_init:int, fnv_prime:int, fnv_size:int) -> int: ...
def fnva(data: bytes, hval_init:int, fnv_prime:int, fnv_size:int) -> int: ...

def fnv0_32(data: bytes, hval_init:int = 0) -> int: ...

def fnv1_32(data:bytes, hval_init:int = 0) -> int: ...

def fnv1a_32(data:bytes, hval_init:int = 0) -> int: ...

def fnv0_64(data:bytes, hval_init:int = 0) -> int: ...

def fnv1_64(data:bytes, hval_init:int = 0) -> int: ...

def fnv1a_64(data:bytes, hval_init:int = 0) -> int: ...
