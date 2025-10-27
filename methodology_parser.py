class MethodologyParser:
    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        try:
            with open(self.file_path, 'r') as f:
                phases = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return phases or ["reconnaissance", "scanning", "exploitation"]
        except FileNotFoundError:
            return ["reconnaissance", "scanning", "exploitation"]