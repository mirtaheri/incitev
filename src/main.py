import yaml


def read_config(file_path = "./config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


config = read_config()
print(config['COMMUNICATION']['CLOUD'])

