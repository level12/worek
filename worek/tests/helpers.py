
class MockCLIExecutor:
    def __init__(self, returncode=0, stderr=b'', stdout=b''):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout

    def __call__(self, *args, **kwargs):
        self.captured_args = args
        self.captured_kwargs = kwargs
        return self
