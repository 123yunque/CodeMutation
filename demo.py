# DYNAPYT: DO NOT INSTRUMENT


from dynapyt.runtime import RuntimeEngine
_rt = RuntimeEngine()

_dynapyt_ast_ = r"D:\pycode\empirical\demo.py" + ".orig"
try:
    print(">>> Target program started! <<<")
    x = _rt._write_(_dynapyt_ast_, 0, 10, [lambda: x])
    for i in range(3):
        x = _rt._write_(_dynapyt_ast_, 2, x + i, [lambda: x])
    print(f">>> Target program finished, x is: {x} <<<")
except Exception as _dynapyt_exception_:
    _rt._catch_(_dynapyt_exception_)
